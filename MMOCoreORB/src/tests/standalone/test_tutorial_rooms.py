#!/usr/bin/env python3
"""Run tutorial room and supply-drum progression against the real Lua scripts.

Uses an installed Lua 5.3/5.4 library and mock game endpoints; does not build or
run Core3. Actual container permissions, client interactions and persistence
still need in-game verification. --source-head checks the current commit's
scripts so the same regression can be demonstrated before an uncommitted fix.
"""

import argparse
import ctypes
import ctypes.util
from pathlib import Path
import subprocess


CORE = Path(__file__).resolve().parents[3]
REPO = CORE.parent
SCRIPTS = (
    "MMOCoreORB/bin/scripts/screenplays/tutorial/tutorial.lua",
    "MMOCoreORB/bin/scripts/screenplays/tutorial/conversations/tutorialRoomTwoGreeterConvoHandler.lua",
)

SETUP = r'''
ScreenPlay = {}
function ScreenPlay:new(object) return setmetatable(object, {__index = self}) end
conv_handler = ScreenPlay
function require(...) return {} end
function registerScreenPlay(...) end
OPEN, MOVEOUT = 1, 2
OBJECTRADIALOPENED, OPENCONTAINER, CLOSECONTAINER = 10, 11, 12
NEWBIEOPENINVENTORY, NEWBIECLOSEINVENTORY, CHAT, NEWBIETUTORIALHOLOCRON = 13, 14, 15, 16
'''

CASES = r'''
local tests = 0
local function check(result, label)
    assert(result, label)
    tests = tests + 1
end
local data, persistent, events, observers, messages = {}, {}, {}, {}, {}
local permissions = {}
local function object(id)
    return {id = id, getObjectID = function(self) return self.id end}
end
local room1, room2 = object(101), object(102)
room1.isCellObject = function() return true end
room2.isCellObject = function() return true end
local building = object(100)
building.cells = {r1 = room1, r2 = room2}
building.isBuildingObject = function() return true end
building.getNamedCell = function(self, name) return self.cells[name] end
local ghost = {addPermissionGroup = function(_, group) permissions[group] = true end}
local player = object(17)
player.parent, player.root = room1.id, building
player.getParentID = function(self) return self.parent end
player.getRootParent = function(self) return self.root end
player.getPlayerObject = function() return ghost end
player.sendSystemMessage = function(_, message) table.insert(messages, message) end
player.playMusicMessage = function() end
player.sendNewbieTutorialEnableHudElement = function() end
player.sendNewbieTutorialRequest = function() end
player.sendOpenHolocronToPageMessage = function() end
local greeter, drum, item = object(200), object(300), object(301)
greeter.setPvpStatusBitmask = function() end
greeter.doAnimation = function() end
drum.clearContainerDefaultAllowPermission = function(self, mask) self.defaultRemoved = mask end
drum.setContainerAllowPermission = function(self, group, mask) self.group, self.allowed = group, mask end
drum.setContainerInheritPermissionsFromParent = function(self, inherit) self.inherit = inherit end
drum.setContainerComponent = function(self, component) self.component = component end
drum.showFlyText = function() end
drum.getContainerObjectsSize = function() return 1 end
drum.getContainerObject = function(_, index) if index == 0 then return item end end
function SceneObject(value) return value end
function CreatureObject(value) return value end
function BuildingObject(value) return value end
function PlayerObject(value) return value end
function LuaConversationScreen(value) return value end
function readData(key) return data[key] or 0 end
function writeData(key, value) data[key] = value end
function deleteData(key) data[key] = nil end
function readScreenPlayData(_, screenplay, key) return persistent[screenplay .. key] or "" end
function writeScreenPlayData(_, screenplay, key, value) persistent[screenplay .. key] = tostring(value) end
function createEvent(delay, screenplay, method, target, argument)
    table.insert(events, {method = method, target = target, argument = argument})
end
function createObserver(event, screenplay, method, target)
    table.insert(observers, {event = event, method = method, target = target})
end
function getSceneObject(id)
    if id == drum.id then return drum end
    if id == greeter.id then return greeter end
end
function spatialChat(...) end
function spawnMobile(_, template, ...)
    if template == "tutorial_room2_greeter" then return greeter end
end
function spawnSceneObject(_, template, ...)
    assert(template == "object/tangible/container/drum/tatt_drum_1.iff")
    return drum
end
function addStartingItemsInto(target, container)
    assert(target == player and container == drum)
    drum.itemsAdded = true
end
local function fire(method)
    for index, event in ipairs(events) do
        if event.method == method then
            table.remove(events, index)
            TutorialScreenPlay[method](TutorialScreenPlay, event.target, event.argument)
            return true
        end
    end
    return false
end
local function observing(method, target)
    for _, observer in ipairs(observers) do
        if observer.method == method and observer.target == target then return true end
    end
    return false
end

-- These checks use the actual room helpers, including root/cell validation.
check(TutorialScreenPlay:isInRoom(player, "r1"), "valid first-room player must be recognized")
check(not TutorialScreenPlay:isInRoom(player, "r2"), "different current cell must not match")
for _, name in ipairs({"", "unknown"}) do
    check(not TutorialScreenPlay:isInRoom(player, name), "invalid room must not match")
end
check(not TutorialScreenPlay:isInRoom(nil, "r1"), "missing player must not match")
check(not TutorialScreenPlay:isInRoom(player, nil), "missing room must not match")
player.parent = 0
check(not TutorialScreenPlay:isInRoom(player, "r1"), "player outside cells must not match")
player.parent, player.root = room1.id, nil
check(not TutorialScreenPlay:isInRoom(player, "r1"), "missing building must not match")
player.root = {isBuildingObject = function() return false end}
check(not TutorialScreenPlay:isInRoom(player, "r1"), "non-building root must not match")
player.root = building
building.cells.r1 = {isCellObject = function() return false end}
check(not TutorialScreenPlay:isInRoom(player, "r1"), "non-cell named object must not match")
building.cells.r1 = room1
check(not TutorialScreenPlay:isRoomComplete(player, "r1"), "fresh room is incomplete")
persistent.tutorialr1Complete = "1"
check(TutorialScreenPlay:isRoomComplete(player, "r1"), "persisted completed room must be recognized")
check(not TutorialScreenPlay:isRoomComplete(player, "r2"), "other room remains incomplete")
check(not TutorialScreenPlay:isRoomComplete(nil, "r1"), "completion with nil player is false")
check(not TutorialScreenPlay:isRoomComplete(player, nil), "completion with nil room is false")
check(not TutorialScreenPlay:isRoomComplete(player, ""), "completion with empty room is false")
TutorialScreenPlay:handleRoomOne(player)
check(#events == 0 and #messages == 0, "completed first room must not replay")
persistent.tutorialr1Complete = nil

-- Follow scheduled first-room instructions through chat and holocron callbacks.
TutorialScreenPlay:handleRoomOne(player)
check(data["17:tutorial:currentStep:r1"] == 1 and #events == 1, "welcome advances and schedules movement")
check(fire("handleRoomOne") and data["17:tutorial:currentStep:r1"] == 2, "movement advances")
check(fire("handleRoomOne") and data["17:tutorial:currentStep:r1"] == 3, "camera advances")
check(fire("handleRoomOne") and observing("chatEvent", player), "chat step installs observer")
TutorialScreenPlay:chatEvent(player, "hello")
check(fire("handleRoomOne") and observing("holocronEvent", player), "chat advances to holocron")
TutorialScreenPlay:holocronEvent(player)
check(fire("handleRoomOne") and data["17:tutorial:currentStep:r1"] == 6, "holocron advances to next-room prompt")

-- Spawn the actual supply drum, move into room two and finish the real officer
-- conversation. Permission must remain gated until the unlock step runs.
TutorialScreenPlay:spawnObjects(player)
check(drum.defaultRemoved == OPEN + MOVEOUT and drum.group == "RoomTwoItemDrum" and
    drum.allowed == OPEN + MOVEOUT and drum.inherit == false and drum.itemsAdded,
    "supply drum starts with group-only access and starter items")
check(not permissions.RoomTwoItemDrum, "player cannot open the drum before the conversation")
player.parent = room2.id
TutorialScreenPlay:changedRoomEvent(player, room2)
check(TutorialScreenPlay:isRoomComplete(player, "r1"), "room transition persists first-room completion")
check(fire("handleRoomTwo") and data["17:tutorial:currentStep:r2"] == 1,
    "room transition starts officer instruction")
check(not permissions.RoomTwoItemDrum, "officer introduction does not prematurely unlock the drum")
local screen = {getScreenID = function() return "in_the_drum" end}
tutorialRoomTwoGreeterConvoHandler:runScreenHandlers(nil, player, greeter, nil, screen)
check(data["17:tutorial:hasDoneRoomTwoConvo"] == 1 and fire("handleRoomTwo"),
    "officer conversation schedules the drum step")
check(permissions.RoomTwoItemDrum and data["17:tutorial:currentStep:r2"] == 2,
    "drum step grants the group needed to open and take supplies")
check(observing("drumOpenEvent", drum) and observing("drumCloseEvent", drum),
    "unlock installs open/close progression observers")
TutorialScreenPlay:drumOpenEvent(drum, player)
check(data["17:tutorial:hasOpenedDrum"] == 1 and observing("drumItemRadialEvent", item),
    "opening drum advances to taking supplies")
TutorialScreenPlay:drumCloseEvent(drum, player)
check(data["17:tutorial:hasClosedDrum"] == 1 and observing("openInventoryEvent", player),
    "closing drum advances to inventory instruction")
local count = #events
persistent.tutorialr2Complete = "1"
TutorialScreenPlay:handleRoomTwo(player)
check(#events == count and data["17:tutorial:currentStep:r2"] == 2,
    "completed supply room must not replay")
print(tests .. " standalone tutorial room checks passed")
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-head", action="store_true")
    args = parser.parse_args()
    library = ctypes.util.find_library("lua5.3") or ctypes.util.find_library("lua5.4")
    if not library:
        raise SystemExit("A Lua 5.3 or 5.4 shared library is required.")
    lua = ctypes.CDLL(library)
    lua.luaL_newstate.restype = ctypes.c_void_p
    lua.luaL_openlibs.argtypes = [ctypes.c_void_p]
    lua.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lua.lua_pcallk.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                             ctypes.c_ssize_t, ctypes.c_void_p]
    lua.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_size_t)]
    lua.lua_tolstring.restype = ctypes.c_char_p
    lua.lua_close.argtypes = [ctypes.c_void_p]
    state = lua.luaL_newstate()
    if not state:
        raise SystemExit("Could not create the standalone Lua state.")
    lua.luaL_openlibs(state)

    def run(source):
        status = lua.luaL_loadstring(state, source.encode())
        if status == 0:
            status = lua.lua_pcallk(state, 0, 0, 0, 0, None)
        if status != 0:
            message = lua.lua_tolstring(state, -1, None)
            raise RuntimeError(message.decode() if message else "Unknown Lua error")

    try:
        run(SETUP)
        for script in SCRIPTS:
            source = (subprocess.check_output(["git", "show", "HEAD:" + script], cwd=REPO, text=True)
                      if args.source_head else (REPO / script).read_text())
            run(source)
        run(CASES)
    finally:
        lua.lua_close(state)


if __name__ == "__main__":
    main()
