from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET

BASE = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Settlement Survival\Settlement Survival_Data\StreamingAssets\zipConfig")
TARGET = Path("mods/AgricultureExpansion")
RESEARCH = "910001"
BUILDING = "910003"
FARM = "3403"
EXPANSION_COLUMN = 4
PLANTATION = "2026"


def read(name):
    return ET.parse(BASE / f"{name}.xml").getroot()


def write(name, root):
    path = TARGET / name
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    ET.parse(path)


def add(parent, tag, value=None):
    element = ET.SubElement(parent, tag)
    element.text = value
    return element


def tech(id, column, row_index, prerequisite, icon, unlock=None):
    row = ET.Element("Techs")
    add(row, "ID", id)
    add(row, "Name", f"AE_Tech_{id}")
    add(row, "Icon", icon)
    add(row, "TechModule", "5")
    position = add(row, "Position")
    add(position, "Int1", str(row_index))
    add(position, "Int2", str(column))
    description = add(add(row, "TechDescribeList"), "TechDescribe")
    add(description, "Name", f"AE_Tech_{id}")
    add(description, "Content", f"AE_Tech_Desc_{id}")
    add(add(row, "PreTechList"), "PreTech", prerequisite)
    if unlock:
        add(add(row, "UnlockBuildingsList"), "UnlockBuildings", unlock)
    return row


def main():
    info = ET.Element("UGCItemInfo")
    for key, value in {
        "Title": "Agriculture Expansion",
        "Des": "Agricultural Research unlocks the Cultivation Hall.",
        "Auther": "Settlement Expanded",
        "Lang": "english",
        "ChangeNote": "0.3.2",
        "SteamKey_Str": None,
    }.items():
        add(info, key, value)
    write("AModConfig.xml", info)

    trees = read("HardTechnology")
    for tree in trees.findall("HardTechnologyConfig"):
        nodes = tree.find("TechsList")
        farm, = nodes.findall(f"Techs[ID='{FARM}']")
        assert nodes.find(f"Techs[ID='{RESEARCH}']") is None
        occupied = {
            (node.findtext("Position/Int1"), node.findtext("Position/Int2"))
            for node in nodes.findall("Techs[TechModule='5']")
        }
        assert all((str(row), str(EXPANSION_COLUMN)) not in occupied for row in range(5))
        icon = farm.findtext("Icon")
        nodes.append(tech(RESEARCH, EXPANSION_COLUMN, 0, FARM, icon, BUILDING))
    write("zipConfig/HardTechnology.xml", trees)

    modules = read("TechnologyModule")
    agriculture, = modules.findall("TechnologyModuleConfig[ID='5']")
    ids = agriculture.find("TechIdList")
    assert RESEARCH not in {node.text for node in ids}
    add(ids, "TechId", RESEARCH)
    module_patch = ET.Element(modules.tag)
    module_patch.append(agriculture)
    write("zipConfig/TechnologyModule.xml", module_patch)

    buildings = read("Building")
    assert buildings.find(f"BuildingConfig[ID='{BUILDING}']") is None
    plantation, = buildings.findall(f"BuildingConfig[ID='{PLANTATION}']")
    hall = deepcopy(plantation)
    hall.find("ID").text = BUILDING
    for field, key in {
        "Name": "AE_Hall", "Des": "AE_Hall_Desc", "ContentDes": "AE_Hall_Desc",
    }.items():
        hall.find(field).text = key
    hall.find("StartPlantDay").text = "55"
    hall.find("EndPlantDay").text = "195"
    resources = hall.find("AllConsumResList")
    resources.clear()
    for item, count in (("3001", "60"), ("3002", "40"), ("4001", "30")):
        cost = add(resources, "AllConsumRes")
        add(cost, "ID", item)
        add(cost, "Num", count)
    building_patch = ET.Element(buildings.tag)
    building_patch.append(hall)
    write("zipConfig/Building.xml", building_patch)

    menus = read("UIButton")
    category, = [
        row for row in menus.findall("UIButtonConfig")
        if row.find(f".//UIButtonConfig[ID='{PLANTATION}']") is not None
    ]
    for group in category.iter("ButtonItemList"):
        button = group.find(f"UIButtonConfig[ID='{PLANTATION}']")
        if button is not None:
            assert group.find(f"UIButtonConfig[ID='{BUILDING}']") is None
            new_button = deepcopy(button)
            new_button.find("ID").text = BUILDING
            new_button.find("Title").text = "Cultivation Hall"
            new_button.find("SelectIdList/SelectId").text = BUILDING
            add(new_button, "TechId", RESEARCH)
            group.insert(list(group).index(button) + 1, new_button)
            break
    else:
        raise ValueError("Plantation menu entry missing")
    menu_patch = ET.Element(menus.tag)
    menu_patch.append(category)
    write("zipConfig/UIButton.xml", menu_patch)

    for lang, strings in {
        "Korean": ("농업연구", "곡물 재배를 위한 재배동을 해금합니다.", "재배동", "일반 밭보다 파종 가능 기간이 긴 재배 시설입니다."),
        "English": ("Agricultural Research", "Unlocks the Cultivation Hall for crop production.", "Cultivation Hall", "A growing facility with a longer sowing window than a regular field."),
    }.items():
        root = ET.Element("ArrayOfLangConfig")
        keys = (f"AE_Tech_{RESEARCH}", f"AE_Tech_Desc_{RESEARCH}", "AE_Hall", "AE_Hall_Desc")
        for key, value in zip(keys, strings):
            config = add(root, "LangConfig")
            add(config, "ID", key)
            translation = add(add(config, "LangList"), "Lang")
            add(translation, "LangType", lang)
            add(translation, "LangValue", value)
        write(f"zipConfig/Lang_{lang}.xml", root)


if __name__ == "__main__":
    main()
