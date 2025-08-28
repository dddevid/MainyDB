import re
import base64
import hashlib
import datetime
import operator
import io
from typing import Dict, List, Any, Union, Optional, Callable
from collections import defaultdict

# Media handling functions
def is_media_type(data):
    """Check if data is a media type that should be encoded"""
    if isinstance(data, bytes):
        return True
    if isinstance(data, str) and data.startswith(('data:image/', 'data:video/')):
        return True
    return False

def encode_media(data):
    """Encode media data to base64 for storage"""
    if isinstance(data, bytes):
        # Raw binary data
        media_type = 'binary'
        encoded = base64.b64encode(data).decode('utf-8')
    elif isinstance(data, str) and data.startswith('data:'):
        # Data URL
        parts = data.split(';base64,')
        if len(parts) != 2:
            return data
        media_type = parts[0].replace('data:', '')
        encoded = parts[1]
    else:
        return data
    
    # Create a hash for caching
    hash_key = hashlib.md5(encoded.encode('utf-8')).hexdigest()
    
    return {
        '__media_type__': media_type,
        'data': encoded,
        'hash': hash_key
    }

def decode_media(encoded_data, cache=None):
    """Decode media data from storage format"""
    if not isinstance(encoded_data, dict) or '__media_type__' not in encoded_data:
        return encoded_data
    
    media_type = encoded_data['__media_type__']
    encoded = encoded_data['data']
    hash_key = encoded_data.get('hash')
    
    # Check cache first
    if cache and hash_key:
        cached_data = cache.get(hash_key)
        if cached_data:
            return cached_data
    
    # Decode based on media type
    if media_type == 'binary':
        decoded = base64.b64decode(encoded)
    else:
        # Reconstruct data URL
        decoded = f"data:{media_type};base64,{encoded}"
    
    # Store in cache
    if cache and hash_key:
        cache.set(hash_key, decoded)
    
    return decoded

# Query operators
def _apply_comparison_operator(doc_val, query_val, op):
    """Apply a comparison operator between document value and query value"""
    # Handle None values specially
    if doc_val is None:
        if op == operator.eq:
            return query_val is None
        elif op == operator.ne:
            return query_val is not None
        return False
    
    # Handle different types
    if not isinstance(doc_val, type(query_val)) and not isinstance(query_val, type(doc_val)):
        if op == operator.eq:
            return False
        elif op == operator.ne:
            return True
        # Try to convert for other comparisons
        try:
            if isinstance(doc_val, (int, float)) and isinstance(query_val, (int, float)):
                # Numeric comparison
                return op(doc_val, query_val)
            elif isinstance(doc_val, str) and isinstance(query_val, (int, float)):
                # Try to convert string to number
                return op(float(doc_val), query_val)
            elif isinstance(query_val, str) and isinstance(doc_val, (int, float)):
                # Try to convert string to number
                return op(doc_val, float(query_val))
            else:
                # Default to string comparison
                return op(str(doc_val), str(query_val))
        except (ValueError, TypeError):
            return False
    
    # Normal comparison
    try:
        return op(doc_val, query_val)
    except TypeError:
        return False

def _get_nested_value(doc, field):
    """Get a value from a document using dot notation for nested fields"""
    if '.' not in field:
        return doc.get(field)
    
    parts = field.split('.')
    value = doc
    
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and part.isdigit():
            idx = int(part)
            if 0 <= idx < len(value):
                value = value[idx]
            else:
                return None
        else:
            return None
    
    return value

def _set_nested_value(doc, field, value):
    """Set a value in a document using dot notation for nested fields"""
    if '.' not in field:
        doc[field] = value
        return
    
    parts = field.split('.')
    target = doc
    
    # Navigate to the correct nested level
    for i, part in enumerate(parts[:-1]):
        if part not in target:
            # Create intermediate objects
            if parts[i+1].isdigit():
                target[part] = []
            else:
                target[part] = {}
        
        if isinstance(target[part], dict):
            target = target[part]
        elif isinstance(target[part], list) and parts[i+1].isdigit():
            idx = int(parts[i+1])
            # Extend list if needed
            while len(target[part]) <= idx:
                target[part].append({})
            target = target[part]
        else:
            # Cannot set nested value on non-object
            return
    
    # Set the value at the final level
    target[parts[-1]] = value

def _unset_nested_value(doc, field):
    """Remove a field from a document using dot notation for nested fields"""
    if '.' not in field:
        if field in doc:
            del doc[field]
        return
    
    parts = field.split('.')
    target = doc
    
    # Navigate to the correct nested level
    for i, part in enumerate(parts[:-1]):
        if part in target:
            if isinstance(target[part], dict):
                target = target[part]
            elif isinstance(target[part], list) and parts[i+1].isdigit():
                idx = int(parts[i+1])
                if 0 <= idx < len(target[part]):
                    target = target[part]
                else:
                    return
            else:
                return
        else:
            return
    
    # Remove the field at the final level
    if parts[-1] in target:
        del target[parts[-1]]

def apply_query_operators(doc, query):
    """Apply MongoDB-style query operators to a document"""
    if not query:
        return True
    
    for field, condition in query.items():
        # Logical operators
        if field == '$and':
            if not all(apply_query_operators(doc, sub_query) for sub_query in condition):
                return False
            continue
        
        elif field == '$or':
            if not any(apply_query_operators(doc, sub_query) for sub_query in condition):
                return False
            continue
        
        elif field == '$nor':
            if any(apply_query_operators(doc, sub_query) for sub_query in condition):
                return False
            continue
        
        elif field == '$not':
            if apply_query_operators(doc, condition):
                return False
            continue
        
        # Regular field query
        if field.startswith('$'):
            # Unsupported top-level operator
            continue
        
        doc_val = _get_nested_value(doc, field)
        
        # Simple equality check
        if not isinstance(condition, dict):
            if doc_val != condition:
                return False
            continue
        
        # Operator-based conditions
        for op_name, op_value in condition.items():
            # Comparison operators
            if op_name == '$eq':
                if not _apply_comparison_operator(doc_val, op_value, operator.eq):
                    return False
            
            elif op_name == '$ne':
                if not _apply_comparison_operator(doc_val, op_value, operator.ne):
                    return False
            
            elif op_name == '$gt':
                if not _apply_comparison_operator(doc_val, op_value, operator.gt):
                    return False
            
            elif op_name == '$gte':
                if not _apply_comparison_operator(doc_val, op_value, operator.ge):
                    return False
            
            elif op_name == '$lt':
                if not _apply_comparison_operator(doc_val, op_value, operator.lt):
                    return False
            
            elif op_name == '$lte':
                if not _apply_comparison_operator(doc_val, op_value, operator.le):
                    return False
            
            elif op_name == '$in':
                if not isinstance(op_value, list):
                    return False
                
                if doc_val is None:
                    if None not in op_value:
                        return False
                elif isinstance(doc_val, list):
                    # For arrays, $in matches if any array element matches any query value
                    if not any(item in op_value for item in doc_val):
                        return False
                elif doc_val not in op_value:
                    return False
            
            elif op_name == '$nin':
                if not isinstance(op_value, list):
                    return False
                
                if doc_val is None:
                    if None in op_value:
                        return False
                elif isinstance(doc_val, list):
                    # For arrays, $nin matches if no array element matches any query value
                    if any(item in op_value for item in doc_val):
                        return False
                elif doc_val in op_value:
                    return False
            
            # Array operators
            elif op_name == '$size':
                if not isinstance(doc_val, list) or len(doc_val) != op_value:
                    return False
            
            elif op_name == '$all':
                if not isinstance(doc_val, list) or not isinstance(op_value, list):
                    return False
                
                if not all(item in doc_val for item in op_value):
                    return False
            
            elif op_name == '$elemMatch':
                if not isinstance(doc_val, list):
                    return False
                
                if not any(apply_query_operators(item, op_value) for item in doc_val if isinstance(item, dict)):
                    return False
    
    return True

def apply_update_operators(doc, update):
    """Apply MongoDB-style update operators to a document"""
    result = doc.copy()
    
    for op_name, op_value in update.items():
        # Direct replacement (no $ operator)
        if not op_name.startswith('$'):
            result[op_name] = op_value
            continue
        
        # Field update operators
        if op_name == '$set':
            for field, value in op_value.items():
                _set_nested_value(result, field, value)
        
        elif op_name == '$unset':
            for field in op_value:
                _unset_nested_value(result, field)
        
        elif op_name == '$inc':
            for field, value in op_value.items():
                current = _get_nested_value(result, field) or 0
                if not isinstance(current, (int, float)):
                    try:
                        current = float(current)
                    except (ValueError, TypeError):
                        current = 0
                _set_nested_value(result, field, current + value)
        
        elif op_name == '$mul':
            for field, value in op_value.items():
                current = _get_nested_value(result, field)
                if current is None:
                    _set_nested_value(result, field, 0)
                elif isinstance(current, (int, float)):
                    _set_nested_value(result, field, current * value)
        
        elif op_name == '$rename':
            for old_field, new_field in op_value.items():
                value = _get_nested_value(result, old_field)
                if value is not None:
                    _set_nested_value(result, new_field, value)
                    _unset_nested_value(result, old_field)
        
        elif op_name == '$min':
            for field, value in op_value.items():
                current = _get_nested_value(result, field)
                if current is None or _apply_comparison_operator(current, value, operator.gt):
                    _set_nested_value(result, field, value)
        
        elif op_name == '$max':
            for field, value in op_value.items():
                current = _get_nested_value(result, field)
                if current is None or _apply_comparison_operator(current, value, operator.lt):
                    _set_nested_value(result, field, value)
        
        elif op_name == '$currentDate':
            for field, value in op_value.items():
                if value is True or value == {'$type': 'date'}:
                    _set_nested_value(result, field, datetime.datetime.now())
                elif isinstance(value, dict) and value.get('$type') == 'timestamp':
                    _set_nested_value(result, field, int(datetime.datetime.now().timestamp()))
        
        # Array update operators
        elif op_name == '$push':
            for field, value in op_value.items():
                current = _get_nested_value(result, field)
                if current is None:
                    current = []
                    _set_nested_value(result, field, current)
                
                if not isinstance(current, list):
                    # Convert to list if not already
                    current = [current]
                    _set_nested_value(result, field, current)
                
                if isinstance(value, dict) and '$each' in value:
                    # Push multiple values
                    items = value['$each']
                    if not isinstance(items, list):
                        items = [items]
                    
                    # Apply slice if specified
                    if '$slice' in value:
                        slice_val = value['$slice']
                        if slice_val < 0:
                            # Keep last N elements
                            current.extend(items)
                            current = current[slice_val:]
                            _set_nested_value(result, field, current)
                            continue
                    
                    # Apply sort if specified
                    if '$sort' in value:
                        sort_val = value['$sort']
                        if isinstance(sort_val, int):
                            # 1 for ascending, -1 for descending
                            current.extend(items)
                            current.sort(reverse=(sort_val == -1))
                        elif isinstance(sort_val, dict):
                            # Sort by specified fields
                            current.extend(items)
                            for sort_field, sort_dir in reversed(list(sort_val.items())):
                                current.sort(
                                    key=lambda x: x.get(sort_field) if isinstance(x, dict) else None,
                                    reverse=(sort_dir == -1)
                                )
                    else:
                        current.extend(items)
                else:
                    # Push single value
                    current.append(value)
        
        elif op_name == '$pop':
            for field, value in op_value.items():
                current = _get_nested_value(result, field)
                if isinstance(current, list) and current:
                    if value == 1:  # Remove last element
                        current.pop()
                    elif value == -1:  # Remove first element
                        current.pop(0)
        
        elif op_name == '$pull':
            for field, value in op_value.items():
                current = _get_nested_value(result, field)
                if not isinstance(current, list):
                    continue
                
                if isinstance(value, dict):
                    # Pull by query
                    current[:] = [item for item in current if not apply_query_operators(item, value)]
                else:
                    # Pull by value
                    current[:] = [item for item in current if item != value]
        
        elif op_name == '$pullAll':
            for field, values in op_value.items():
                current = _get_nested_value(result, field)
                if not isinstance(current, list) or not isinstance(values, list):
                    continue
                
                current[:] = [item for item in current if item not in values]
        
        elif op_name == '$addToSet':
            for field, value in op_value.items():
                current = _get_nested_value(result, field)
                if current is None:
                    current = []
                    _set_nested_value(result, field, current)
                
                if not isinstance(current, list):
                    # Convert to list if not already
                    current = [current]
                    _set_nested_value(result, field, current)
                
                if isinstance(value, dict) and '$each' in value:
                    # Add multiple unique values
                    for item in value['$each']:
                        if item not in current:
                            current.append(item)
                elif value not in current:
                    # Add single unique value
                    current.append(value)
    
    return result

# Aggregation pipeline
def apply_aggregation_pipeline(documents, pipeline):
    """Apply MongoDB-style aggregation pipeline to documents"""
    result = documents.copy()
    
    for stage in pipeline:
        stage_op = list(stage.keys())[0]
        stage_params = stage[stage_op]
        
        if stage_op == '$match':
            result = [doc for doc in result if apply_query_operators(doc, stage_params)]
        
        elif stage_op == '$project':
            new_result = []
            for doc in result:
                new_doc = {}
                
                # Handle inclusion/exclusion
                include_mode = None
                
                # Determine if we're in include or exclude mode
                include_values = [v for v in stage_params.values() if v == 1]
                exclude_values = [v for v in stage_params.values() if v == 0]
                
                if include_values and exclude_values:
                    # Can't mix include and exclude except for _id
                    non_id_projection = {k: v for k, v in stage_params.items() if k != '_id'}
                    non_id_include = [v for v in non_id_projection.values() if v == 1]
                    non_id_exclude = [v for v in non_id_projection.values() if v == 0]
                    
                    if non_id_include and non_id_exclude:
                        raise ValueError("Cannot mix inclusive and exclusive projections")
                    
                    include_mode = bool(non_id_include)
                else:
                    include_mode = bool(include_values)
                
                # Process each field in the projection
                for field, value in stage_params.items():
                    if value == 1:  # Include field
                        if field in doc:
                            new_doc[field] = doc[field]
                    elif value == 0:  # Exclude field
                        if include_mode is False:
                            for k, v in doc.items():
                                if k != field:
                                    new_doc[k] = v
                    elif isinstance(value, dict):  # Expression
                        # Handle expressions like $add, $multiply, etc.
                        if '$add' in value:
                            operands = [_get_nested_value(doc, op) if isinstance(op, str) and op.startswith('$') 
                                      else op for op in value['$add']]
                            if all(isinstance(op, (int, float)) for op in operands):
                                new_doc[field] = sum(operands)
                        
                        elif '$multiply' in value:
                            operands = [_get_nested_value(doc, op) if isinstance(op, str) and op.startswith('$') 
                                      else op for op in value['$multiply']]
                            if all(isinstance(op, (int, float)) for op in operands):
                                result_val = 1
                                for op in operands:
                                    result_val *= op
                                new_doc[field] = result_val
                        
                        elif '$substr' in value:
                            params = value['$substr']
                            if len(params) >= 3:
                                string_val = _get_nested_value(doc, params[0]) if isinstance(params[0], str) else str(params[0])
                                start = params[1]
                                length = params[2]
                                if isinstance(string_val, str) and isinstance(start, int) and isinstance(length, int):
                                    new_doc[field] = string_val[start:start+length]
                
                # Special handling for _id which is included by default
                if '_id' not in stage_params or stage_params['_id'] == 1:
                    if '_id' in doc:
                        new_doc['_id'] = doc['_id']
                
                new_result.append(new_doc)
            
            result = new_result
        
        elif stage_op == '$group':
            groups = defaultdict(list)
            id_field = stage_params['_id']
            
            # Group documents
            for doc in result:
                # Determine group key
                if id_field is None:
                    group_key = None
                elif isinstance(id_field, str) and id_field.startswith('$'):
                    # Simple field reference
                    field_name = id_field[1:]  # Remove $ prefix
                    group_key = _get_nested_value(doc, field_name)
                elif isinstance(id_field, dict):
                    # Complex ID expression
                    group_key = {}
                    for k, v in id_field.items():
                        if isinstance(v, str) and v.startswith('$'):
                            field_name = v[1:]  # Remove $ prefix
                            group_key[k] = _get_nested_value(doc, field_name)
                        else:
                            group_key[k] = v
                    # Convert dict to tuple for hashability
                    group_key = tuple(sorted((k, str(v)) for k, v in group_key.items()))
                else:
                    group_key = id_field
                
                groups[group_key].append(doc)
            
            # Apply accumulator operations
            new_result = []
            for group_key, group_docs in groups.items():
                new_doc = {'_id': group_key}
                
                for field, accumulator in stage_params.items():
                    if field == '_id':
                        continue
                    
                    # Handle different accumulators
                    if isinstance(accumulator, dict):
                        acc_op = list(accumulator.keys())[0]
                        acc_field = accumulator[acc_op]
                        
                        if isinstance(acc_field, str) and acc_field.startswith('$'):
                            field_name = acc_field[1:]  # Remove $ prefix
                            
                            if acc_op == '$sum':
                                new_doc[field] = sum(_get_nested_value(doc, field_name) or 0 for doc in group_docs)
                            
                            elif acc_op == '$avg':
                                values = [_get_nested_value(doc, field_name) for doc in group_docs]
                                values = [v for v in values if isinstance(v, (int, float))]
                                new_doc[field] = sum(values) / len(values) if values else None
                            
                            elif acc_op == '$min':
                                values = [_get_nested_value(doc, field_name) for doc in group_docs]
                                values = [v for v in values if v is not None]
                                new_doc[field] = min(values) if values else None
                            
                            elif acc_op == '$max':
                                values = [_get_nested_value(doc, field_name) for doc in group_docs]
                                values = [v for v in values if v is not None]
                                new_doc[field] = max(values) if values else None
                            
                            elif acc_op == '$push':
                                new_doc[field] = [_get_nested_value(doc, field_name) for doc in group_docs]
                            
                            elif acc_op == '$addToSet':
                                values = [_get_nested_value(doc, field_name) for doc in group_docs]
                                new_doc[field] = list(set(str(v) for v in values))
                            
                            elif acc_op == '$first':
                                values = [_get_nested_value(doc, field_name) for doc in group_docs]
                                new_doc[field] = values[0] if values else None
                            
                            elif acc_op == '$last':
                                values = [_get_nested_value(doc, field_name) for doc in group_docs]
                                new_doc[field] = values[-1] if values else None
                        
                        elif acc_op == '$count':
                            new_doc[field] = len(group_docs)
                
                new_result.append(new_doc)
            
            result = new_result
        
        elif stage_op == '$sort':
            for field, direction in reversed(list(stage_params.items())):
                reverse = direction == -1
                result.sort(
                    key=lambda x: _get_nested_value(x, field) if _get_nested_value(x, field) is not None else (float('-inf') if reverse else float('inf')),
                    reverse=reverse
                )
        
        elif stage_op == '$limit':
            result = result[:stage_params]
        
        elif stage_op == '$skip':
            result = result[stage_params:]
        
        elif stage_op == '$unwind':
            new_result = []
            if isinstance(stage_params, str):
                # Simple syntax: "$fieldName"
                field = stage_params[1:]  # Remove $ prefix
                for doc in result:
                    array_value = _get_nested_value(doc, field)
                    if isinstance(array_value, list):
                        for item in array_value:
                            new_doc = doc.copy()
                            _set_nested_value(new_doc, field, item)
                            new_result.append(new_doc)
                    else:
                        # Skip or include non-array values based on MongoDB behavior
                        new_result.append(doc)
            else:
                # Extended syntax: {path: "$fieldName", ...}
                field = stage_params['path'][1:]  # Remove $ prefix
                include_array_index = stage_params.get('includeArrayIndex')
                preserve_null_and_empty = stage_params.get('preserveNullAndEmptyArrays', False)
                
                for doc in result:
                    array_value = _get_nested_value(doc, field)
                    
                    if isinstance(array_value, list) and array_value:
                        for i, item in enumerate(array_value):
                            new_doc = doc.copy()
                            _set_nested_value(new_doc, field, item)
                            
                            if include_array_index:
                                _set_nested_value(new_doc, include_array_index, i)
                            
                            new_result.append(new_doc)
                    elif preserve_null_and_empty:
                        new_result.append(doc)
            
            result = new_result
        
        elif stage_op == '$addFields':
            for doc in result:
                for field, value in stage_params.items():
                    if isinstance(value, dict) and len(value) == 1:
                        # Handle expressions
                        op = list(value.keys())[0]
                        if op.startswith('$'):
                            if op == '$add':
                                operands = []
                                for operand in value[op]:
                                    if isinstance(operand, str) and operand.startswith('$'):
                                        operands.append(_get_nested_value(doc, operand[1:]))  # Remove $ prefix
                                    else:
                                        operands.append(operand)
                                
                                if all(isinstance(op, (int, float)) for op in operands):
                                    _set_nested_value(doc, field, sum(operands))
                            
                            elif op == '$multiply':
                                operands = []
                                for operand in value[op]:
                                    if isinstance(operand, str) and operand.startswith('$'):
                                        operands.append(_get_nested_value(doc, operand[1:]))  # Remove $ prefix
                                    else:
                                        operands.append(operand)
                                
                                if all(isinstance(op, (int, float)) for op in operands):
                                    result_val = 1
                                    for op in operands:
                                        result_val *= op
                                    _set_nested_value(doc, field, result_val)
                            
                            elif op == '$concat':
                                strings = []
                                for operand in value[op]:
                                    if isinstance(operand, str) and operand.startswith('$'):
                                        val = _get_nested_value(doc, operand[1:])  # Remove $ prefix
                                        strings.append(str(val) if val is not None else '')
                                    else:
                                        strings.append(str(operand))
                                
                                _set_nested_value(doc, field, ''.join(strings))
                    elif isinstance(value, str) and value.startswith('$'):
                        # Field reference
                        _set_nested_value(doc, field, _get_nested_value(doc, value[1:]))  # Remove $ prefix
                    else:
                        # Literal value
                        _set_nested_value(doc, field, value)
        
        elif stage_op == '$lookup':
            # This is a simplified version as we don't have access to other collections
            # In a real implementation, this would join with another collection
            from_collection = stage_params.get('from')
            local_field = stage_params.get('localField')
            foreign_field = stage_params.get('foreignField')
            as_field = stage_params.get('as')
            
            # Since we can't access other collections in this simplified version,
            # we'll just add an empty array for the joined field
            for doc in result:
                _set_nested_value(doc, as_field, [])
        
        elif stage_op == '$count':
            count = len(result)
            result = [{stage_params: count}]
    
    return result

# Indexing functions
def build_index(documents, keys, existing_index=None):
    """Build an index for the specified keys"""
    if existing_index is None:
        index = defaultdict(list)
    else:
        index = existing_index
    
    for i, doc in enumerate(documents):
        # Create composite key
        key_values = []
        for k in keys:
            value = _get_nested_value(doc, k)
            # Handle non-hashable types
            if isinstance(value, (list, dict)):
                value = str(value)
            key_values.append(value)
        
        # Use tuple for composite key (hashable)
        composite_key = tuple(key_values)
        index[composite_key].append(i)
    
    return index

def query_with_index(documents, query, indexes):
    """Try to use an index to speed up a query"""
    # Check if we can use an index for this query
    for index_name, index_data in indexes.items():
        index_keys = index_name.split('_')[::2]  # Extract field names from index name
        
        # Check if query uses indexed fields
        can_use_index = False
        index_query_values = {}
        
        for field in index_keys:
            if field in query and isinstance(query[field], (dict, int, float, str, bool, type(None))):
                can_use_index = True
                if isinstance(query[field], dict):
                    # Handle operators
                    if '$eq' in query[field]:
                        index_query_values[field] = query[field]['$eq']
                    elif all(op not in query[field] for op in ['$ne', '$gt', '$gte', '$lt', '$lte', '$in', '$nin']):
                        # Can't use index efficiently with these operators
                        can_use_index = False
                        break
                else:
                    # Direct equality match
                    index_query_values[field] = query[field]
        
        if can_use_index and index_query_values:
            # Create composite key for index lookup
            key_values = []
            for k in index_keys:
                if k in index_query_values:
                    value = index_query_values[k]
                    # Handle non-hashable types
                    if isinstance(value, (list, dict)):
                        value = str(value)
                    key_values.append(value)
                else:
                    # If we don't have all keys, we can't use the index efficiently
                    can_use_index = False
                    break
            
            if can_use_index:
                # Use tuple for composite key lookup
                composite_key = tuple(key_values)
                if composite_key in index_data:
                    # Get documents by index
                    doc_indices = index_data[composite_key]
                    candidates = [documents[i] for i in doc_indices]
                    
                    # Apply remaining query conditions
                    remaining_query = {k: v for k, v in query.items() if k not in index_query_values}
                    if not remaining_query:
                        return candidates
                    else:
                        return [doc for doc in candidates if apply_query_operators(doc, remaining_query)]
    
    # No suitable index found
    return None