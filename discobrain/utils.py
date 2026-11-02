from isocodes import ISONamespaceRecord
import unicode_blocks

from isocodes import script_names


def most_common_script(text: str) -> str:
    """
    Takes in an input string, returns the most common
    unicode script in ISO code format.
    """
    blocks: dict[str, int] = {}
    for c in text:
        block = unicode_blocks.of(c).name
        if blocks.get(block):
            blocks[block] += 1
        else:
            blocks[block] = 1
    most_common = max(blocks.items(), key=lambda x: x[1])[0]
    print(most_common)
    if "Latin" in most_common:
        return "Latn"
    results = script_names.find(name=most_common.split(" ")[0])
    if isinstance(results, ISONamespaceRecord):
        alpha_4 = results.get("alpha_4")
        if alpha_4:
            return alpha_4
    return ""
    # remove all puncatuation and space from the sample
    # iterate through, building a guess of the script
