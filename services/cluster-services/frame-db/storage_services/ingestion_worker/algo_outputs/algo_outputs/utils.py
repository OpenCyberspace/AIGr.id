import collections

def nested_dict_iter(nested, parent):
    for key, value in nested.items():
        if isinstance(value, collections.Mapping):
            parent = key
            for inner_key, inner_value in nested_dict_iter(value, parent):
                yield parent + "__" + inner_key, inner_value
        else:
            yield key, value


def to_flat_dict(nested):
    flat_dict = {}

    for k, v in nested_dict_iter(nested, ""):
        flat_dict[k] = v
    
    return flat_dict