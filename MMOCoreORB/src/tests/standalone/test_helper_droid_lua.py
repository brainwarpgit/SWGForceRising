#!/usr/bin/env python3
"""Run the production helper scripts through Lua with mock game endpoints.

Requires Python 3 and an installed Lua 5.3/5.4 shared library. No Core3 build,
execution, engine3 reads, or generated files. These checks cover screenplay
behavior; the C++ binding, spawning, pet state and persistence need game tests.
"""

import ctypes
import ctypes.util
from pathlib import Path


CORE_ROOT = Path(__file__).resolve().parents[3]
LUA_ROOT = CORE_ROOT / "bin/scripts/screenplays/themepark/helper_droid"

SETUP = r'''
ScreenPlay = {}
function ScreenPlay:new(object)
    setmetatable(object, {__index = self})
    return object
end
function require(name) return {} end
function registerScreenPlay(...) end
enabled = false
function isHelperDroidEnabled() return enabled end
'''

CASES = r'''
local tests = 0
local function check(condition, label)
    assert(condition, label)
    tests = tests + 1
end

-- Engine APIs intentionally do not exist yet: every public action, queued
-- callback and observer must return before it can access or modify game state.
local dummy = {}
for _, screenplay in ipairs({HelperDroid, HelperDroidQuest}) do
    for name, method in pairs(screenplay) do
        if type(method) == "function" and name ~= "noCallback" and name ~= "checkHasReward" then
            local result = method(screenplay, dummy, dummy, "scout", 1)
            check(result == (name:sub(1, 6) == "notify" and 0 or nil),
                "disabled entrypoint touched game state or removed an observer: " .. name)
        end
    end
end

local effects, data, strings, quests, vectors
local function reset()
    effects = {sounds = 0, dialogs = 0, holocron = 0, messages = 0,
        items = 0, events = {}, chats = 0, credits = 0, xp = 0}
    data, strings, quests, vectors = {}, {}, {}, {}
end
reset()
local inventory = {isContainerFullRecursive = function() return false end}
local player = {
    getObjectID = function() return 17 end,
    playMusicMessage = function() effects.sounds = effects.sounds + 1 end,
    sendOpenHolocronToPageMessage = function() effects.holocron = effects.holocron + 1 end,
    getFirstName = function() return "Tester" end,
    hasSkill = function(_, skill) return skill == "outdoors_scout_novice" end,
    getSlottedObject = function() return inventory end,
    sendSystemMessage = function() effects.messages = effects.messages + 1 end,
    isCreatureObject = function() return true end,
    awardExperience = function(_, _, amount) effects.xp = effects.xp + amount end,
    addCashCredits = function(_, amount) effects.credits = effects.credits + amount end,
}
local droid = {
    getObjectID = function() return 99 end,
    getCustomObjectName = function() return "Helper" end,
}
function SceneObject(object) return object end
function CreatureObject(object) return object end
function getRandomNumber(_) return 1 end
function writeData(key, value) data[key] = value end
function readData(key) return data[key] or 0 end
function deleteData(key) data[key] = nil end
function writeStringData(key, value) strings[key] = value end
function readStringData(key) return strings[key] or "" end
function deleteStringData(key) strings[key] = nil end
function writeStringVectorSharedMemory(key, value) vectors[key] = value end
function readStringVectorSharedMemory(key) return vectors[key] or {} end
function deleteStringVectorSharedMemory(key) vectors[key] = nil end
function getQuestStatus(key) return quests[key] end
function setQuestStatus(key, value) quests[key] = value end
function getSceneObject(id) if id == 99 then return droid end end
function spatialChat(...) effects.chats = effects.chats + 1 end
function createEvent(delay, screenplay, callback, object, argument)
    table.insert(effects.events, {screenplay, callback, object, argument})
end
function giveItem(...)
    effects.items = effects.items + 1
    return {getDisplayedName = function() return "Test item" end}
end
function LuaStringIdChatParameter(...)
    return {setDI = function() end, setTT = function() end,
        setTU = function() end, _getObject = function() return {} end}
end
local function dialog(...)
    return setmetatable({
        sendTo = function() effects.dialogs = effects.dialogs + 1 end,
    }, {__index = function() return function() end end})
end
SuiMessageBox = {new = dialog}
SuiListBox = {new = dialog}

enabled = true
HelperDroid:spaceInformation(droid, player, "travel")
check(effects.sounds == 1 and effects.dialogs == 1, "enabled information dialog")
HelperDroid:helperInformation(droid, player, "general")
check(effects.sounds == 2 and effects.holocron == 1, "enabled holocron help")
HelperDroid:greetPlayer(player, droid)
check(effects.dialogs == 2 and data["17:HelperDroidID:"] == 99 and
    #vectors["17:HelperDroid:playerProfessions:"] == 1, "enabled greeting")
HelperDroid:skillTrained(droid, player, "outdoors_scout_novice")
check(#effects.events == 1 and effects.events[1][2] == "giveProfessionItem" and
    effects.chats == 1, "enabled novice training schedules starter item")

-- A deferred grant queued before disabling must not bypass the switch.
local event = effects.events[1]
enabled = false
_G[event[1]][event[2]](_G[event[1]], event[3], event[4])
check(effects.items == 0, "disabled deferred item callback")
enabled = true
_G[event[1]][event[2]](_G[event[1]], event[3], event[4])
check(effects.items == 1, "re-enabled deferred item callback")
HelperDroidQuest.questsEnabled = false
HelperDroidQuest:giveProfessionItem(player, "artisan")
check(effects.items == 1, "existing quest switch still applies")
HelperDroidQuest.questsEnabled = true

reset()
HelperDroidQuest:startSui(droid, player, "scout")
check(effects.dialogs == 1 and strings["17:HelperDroid:profession:"] == "scout",
    "enabled quest introduction")
data["17:scout:HelperDroid:questStatus:"] = 5
enabled = false
local result = HelperDroidQuest:notifyCampDeployed(player, dummy)
check(result == 0 and #effects.events == 0 and
    quests["17:scout:HelperDroid:completeQuests:"] == nil and
    data["17:scout:HelperDroid:questStatus:"] == 5, "disabled observer preserves progress")
enabled = true
result = HelperDroidQuest:notifyCampDeployed(player, dummy)
check(result == 1 and #effects.events == 1 and
    quests["17:scout:HelperDroid:completeQuests:"] == 5,
    "re-enabled observer completes the existing quest")
enabled = false
event = effects.events[1]
_G[event[1]][event[2]](_G[event[1]], event[3], event[4])
check(effects.xp == 0 and effects.credits == 0 and effects.dialogs == 1,
    "disabled reward callback emits no reward or dialog")

-- Exercise the regular enabled reward path without altering its implementation.
enabled = true
quests["17:scout:HelperDroid:completeQuests:"] = 2
data["17:scout:HelperDroid:questStatus:"] = 2
HelperDroidQuest:giveReward(player, "scout")
check(effects.xp == 50 and effects.credits == 100 and effects.dialogs == 2,
    "enabled rewards and next quest dialog are preserved")
print(tests .. " standalone helper droid Lua checks passed")
'''


def main():
    library = ctypes.util.find_library("lua5.3") or ctypes.util.find_library("lua5.4")
    if not library:
        raise SystemExit("A Lua 5.3 or 5.4 shared library is required.")
    lua = ctypes.CDLL(library)
    lua.luaL_newstate.restype = ctypes.c_void_p
    lua.luaL_openlibs.argtypes = [ctypes.c_void_p]
    lua.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lua.lua_pcallk.argtypes = [
        ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_ssize_t, ctypes.c_void_p,
    ]
    lua.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_size_t)]
    lua.lua_tolstring.restype = ctypes.c_char_p
    lua.lua_close.argtypes = [ctypes.c_void_p]
    state = lua.luaL_newstate()
    if not state:
        raise SystemExit("Could not create the standalone Lua state.")
    lua.luaL_openlibs(state)

    def run(source):
        result = lua.luaL_loadstring(state, source.encode())
        if result == 0:
            result = lua.lua_pcallk(state, 0, 0, 0, 0, None)
        if result != 0:
            message = lua.lua_tolstring(state, -1, None)
            raise RuntimeError(message.decode() if message else "Unknown Lua error")

    try:
        run(SETUP)
        for filename in ("helper_droid.lua", "helper_droid_quest.lua"):
            run((LUA_ROOT / filename).read_text())
        run(CASES)
    finally:
        lua.lua_close(state)


if __name__ == "__main__":
    main()
