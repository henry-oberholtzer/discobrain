def safe_index(lst, idx, default = ''):
    try:
        return lst[idx]
    except IndexError:
        return default

