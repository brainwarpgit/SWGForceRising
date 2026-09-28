#!/usr/bin/env python3
"""Exercise the production faction cap and recruiter Lua without Core3.

The actual isHighestRank method is compiled against a tiny rank-count mock,
then exposed directly to the production recruiter Lua as its native callback.
Requires a C++17 compiler and Lua 5.3/5.4 shared library. Temporary files stay
under bin. No Core3 components or engine3 headers are built or accessed.
--source-head runs the current commit's source to demonstrate regressions.
Real TRE loading, client dialogue and character persistence need game tests.
"""

import argparse
import ctypes
import ctypes.util
import os
from pathlib import Path
import shlex
import subprocess
import tempfile


CORE = Path(__file__).resolve().parents[3]
REPO = CORE.parent
HEADER = "MMOCoreORB/src/server/zone/managers/faction/FactionManager.h"
ADMIN = "MMOCoreORB/src/server/zone/objects/creature/commands/SetFactionCommand.h"
RECRUITER = "MMOCoreORB/bin/scripts/screenplays/gcw/recruiters/recruiterConvoHandler.lua"

SETUP = r'''
conv_handler = {}
function conv_handler:new(object) return setmetatable(object, {__index = self}) end
function require(...) return {} end
'''

CASES = r'''
local tests = 0
local function check(result, label) assert(result, label); tests = tests + 1 end
local lookups = 0
local invalidCostRank
-- Effective rank.iff rows above colonel; synthetic values cover alternate
-- table lengths without coupling the test to a machine's TRE collection.
local upperRankCosts = {[16] = 6500, [17] = 6500, [18] = 7000,
    [19] = 7000, [20] = 7500, [21] = 7500}
function CreatureObject(object) return object end
function PlayerObject(object) return object end
function LuaConversationScreen(object) return object end
function LuaConversationTemplate(object) return object end
function getRankCost(rank)
    assert(rank >= 0 and rank < rankRows, "out-of-range rank cost lookup: " .. rank)
    lookups = lookups + 1
    if rank == invalidCostRank then return -1 end
    return upperRankCosts[rank] or (rank + 1) * 100
end
function getRankName(rank)
    assert(rank >= 0 and rank < rankRows, "out-of-range rank name lookup: " .. rank)
    return "rank_" .. rank
end
function useCovertOvert() return false end
function readData(...) return 0 end
recruiterScreenplay = {
    getMinimumFactionStanding = function() return 200 end,
    getRecruiterFaction = function(_, npc) return npc.faction end,
    getRecruiterFactionHashCode = function(_, npc) return npc.faction end,
    getFactionFromHashCode = function(_, faction) return faction end,
    getRecruiterEnemyFactionHashCode = function(_, npc)
        return npc.faction == "rebel" and "imperial" or "rebel"
    end,
    getRecruiterEnemyFaction = function(_, npc)
        return npc.faction == "rebel" and "imperial" or "rebel"
    end,
}
local function screen(id)
    return {
        id = id, options = {},
        getScreenID = function(self) return self.id end,
        cloneScreen = function(self) return screen(self.id) end,
        addOption = function(self, text, nextScreen) table.insert(self.options, nextScreen) end,
        setDialogTextTO = function(self, tableName, name) self.rankName = name end,
        setDialogTextDI = function(self, value) self.cost = value end,
        setDialogTextStringId = function(self, value) self.dialog = value end,
        removeAllOptions = function(self) self.options = {} end,
        setStopConversation = function(self, value) self.stopped = value end,
    }
end
local template = {getScreen = function(_, id) return screen(id) end}
local function player(rank, faction, points)
    local ghost = {
        standing = {[faction] = points}, charges = 0,
        getFactionStanding = function(self, faction) return self.standing[faction] or 0 end,
        decreaseFactionStanding = function(self, faction, cost)
            self.standing[faction] = self.standing[faction] - cost
            self.charges = self.charges + 1
        end,
    }
    return {
        rank = rank, faction = faction, ghost = ghost, changes = 0,
        getPlayerObject = function(self) return self.ghost end,
        getFactionRank = function(self) return self.rank end,
        setFactionRank = function(self, rank) self.rank = rank; self.changes = self.changes + 1 end,
        getFaction = function(self) return self.faction end,
        isChangingFactionStatus = function() return false end,
        isOnLeave = function() return false end,
        isCovert = function() return true end,
        getObjectID = function() return 17 end,
        sendSystemMessage = function() end,
    }
end
local function run(id, p, faction)
    return RecruiterConvoHandler:runScreenHandlers(template, p, {faction = faction}, 0, screen(id))
end
local function offer(p, faction)
    local result = screen("greet_member_start_covert")
    RecruiterConvoHandler:updateScreenWithPromotions(p, template, result, faction)
    return #result.options > 0
end

-- Both factions use the loaded row count, and charge precisely the next
-- rank's configured cost while retaining the minimum standing reserve.
rankRows = 22
for _, faction in ipairs({"rebel", "imperial"}) do
    for _, rank in ipairs({15, 20}) do
        local cost = getRankCost(rank + 1)
        local p = player(rank, faction, cost + 200)
        check(offer(p, faction), "promotion must be offered above the old colonel cap")
        local confirm = run("confirm_promotion", p, faction)
        check(confirm.rankName == "rank_" .. (rank + 1), "confirmation names the next table rank")
        run("accepted_promotion", p, faction)
        check(p.rank == rank + 1 and p.ghost.standing[faction] == 200 and p.ghost.charges == 1,
            "promotion increments once and charges only the configured cost")
        p = player(rank, faction, cost + 199)
        check(not offer(p, faction), "insufficient standing does not offer promotion")
        local reject = run("accepted_promotion", p, faction)
        check(reject.id == "not_enough_points" and reject.cost == cost and p.rank == rank and
            p.ghost.standing[faction] == cost + 199 and p.ghost.charges == 0,
            "acceptance rechecks points without charging on failure")
    end
    local p = player(21, faction, 100000)
    local before = lookups
    check(not offer(p, faction) and lookups == before, "last table rank has no promotion offer")
end

-- A different table length changes the Lua menu boundary through the real
-- native predicate, without changing any script-side rank constants.
for _, count in ipairs({1, 4, 16, 24}) do
    rankRows = count
    local p = player(count - 1, "rebel", 100000)
    check(not offer(p, "rebel"), "table's final rank has no offer")
    if count > 1 then
        p.rank = count - 2
        check(offer(p, "rebel"), "table's penultimate rank has an offer")
    end
end
rankRows = 22
check(not offer(player(-1, "rebel", 100000), "rebel"), "negative ranks remain ineligible")
for _, faction in ipairs({"rebel", "imperial"}) do
    for _, rank in ipairs({-1, 21, 25}) do
        for _, id in ipairs({"confirm_promotion", "accepted_promotion"}) do
            local p = player(rank, faction, 100000)
            local before = lookups
            local result = run(id, p, faction)
            check(result.stopped and #result.options == 0 and
                result.dialog == "@faction_recruiter:promotion_max_rank" and
                p.rank == rank and p.changes == 0 and p.ghost.charges == 0 and
                p.ghost.standing[faction] == 100000 and lookups == before,
                "invalid/stale promotion must stop before any rank lookup or charge")
        end
    end
end
invalidCostRank = 16
local p = player(15, "rebel", 100000)
check(not offer(p, "rebel"), "invalid next-rank cost suppresses the menu option")
for _, id in ipairs({"confirm_promotion", "accepted_promotion"}) do
    local result = run(id, p, "rebel")
    check(result.stopped and p.rank == 15 and p.ghost.charges == 0,
        "invalid next-rank cost cannot promote or refund negative cost")
end
invalidCostRank = nil
p = player(15, "rebel", 100000)
check(offer(p, "rebel"), "valid promotion is offered before table changes")
rankRows = 16
local result = run("accepted_promotion", p, "rebel")
check(result.stopped and p.rank == 15 and p.ghost.charges == 0,
    "acceptance rechecks the current table boundary")
print(tests .. " standalone recruiter Lua checks passed")
'''


def method(source, signature):
    start = source.index(signature)
    end = source.index("}", start) + 1
    return source[start:end]


def run_lua(source, predicate):
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
    lua.lua_tointegerx.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
    lua.lua_tointegerx.restype = ctypes.c_longlong
    lua.lua_getglobal.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lua.lua_setglobal.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lua.lua_settop.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lua.lua_pushboolean.argtypes = [ctypes.c_void_p, ctypes.c_int]
    callback_type = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p)
    lua.lua_pushcclosure.argtypes = [ctypes.c_void_p, callback_type, ctypes.c_int]
    lua.lua_close.argtypes = [ctypes.c_void_p]

    @callback_type
    def highest(state):
        rank = lua.lua_tointegerx(state, 1, None)
        lua.lua_getglobal(state, b"rankRows")
        count = lua.lua_tointegerx(state, -1, None)
        lua.lua_settop(state, -2)
        lua.lua_pushboolean(state, predicate(count, rank))
        return 1

    state = lua.luaL_newstate()
    if not state:
        raise SystemExit("Could not create the standalone Lua state.")
    lua.luaL_openlibs(state)

    def run(text):
        status = lua.luaL_loadstring(state, text.encode())
        if status == 0:
            status = lua.lua_pcallk(state, 0, 0, 0, 0, None)
        if status != 0:
            message = lua.lua_tolstring(state, -1, None)
            raise RuntimeError(message.decode() if message else "Unknown Lua error")

    try:
        lua.lua_pushcclosure(state, highest, 0)
        lua.lua_setglobal(state, b"isHighestRank")
        run(SETUP)
        run(source)
        run(CASES)
    finally:
        lua.lua_close(state)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-head", action="store_true")
    args = parser.parse_args()

    def read(path):
        if args.source_head:
            return subprocess.check_output(["git", "show", "HEAD:" + path], cwd=REPO, text=True)
        return (REPO / path).read_text()

    header = read(HEADER)
    maximum = method(header, "int getHighestRank()") if "int getHighestRank()" in header else ""
    source = "#include <algorithm>\nstruct Math { static int max(int a, int b) { return std::max(a,b); } };\n"
    source += "struct RankList { int count; int getCount() const { return count; } };\n"
    source += "struct FactionManager { RankList factionRanks; " + maximum
    source += method(header, "bool isHighestRank(int rank)")
    source += " static FactionManager*& active() { static FactionManager* value = nullptr; return value; }"
    source += " static FactionManager* instance() { return active(); } };\n"
    source += 'extern "C" int highest(int count, int rank) { return FactionManager{{count}}.isHighestRank(rank); }\n'
    admin = read(ADMIN)
    clamp = admin[admin.index("\t\t\tif (rank < 0)"):admin.index("\n\t\t\ttargetRank = rank;")]
    source += 'extern "C" int clampRank(int count, int rank) { FactionManager manager{{count}}; '
    source += 'FactionManager::active() = &manager; ' + clamp + '\nreturn rank; }\n'
    with tempfile.TemporaryDirectory(prefix="faction-rank-check-", dir=CORE / "bin") as temporary:
        directory = Path(temporary)
        cpp, shared = directory / "check.cpp", directory / "check.so"
        cpp.write_text(source)
        compiler = shlex.split(os.environ.get("CXX", "c++"))
        subprocess.run(compiler + ["-std=c++17", "-Wall", "-Wextra", "-fPIC", "-shared",
                                  str(cpp), "-o", str(shared)], check=True)
        native = ctypes.CDLL(str(shared))
        native.highest.argtypes = [ctypes.c_int, ctypes.c_int]
        native.highest.restype = ctypes.c_int
        native.clampRank.argtypes = [ctypes.c_int, ctypes.c_int]
        native.clampRank.restype = ctypes.c_int
        checks = 0
        for count in (22, 4, 16, 24, 1, 0):
            for rank in sorted({0, count - 2, count - 1, count, count + 2, 15, 16, 20, 21}):
                highest = max(0, count - 1)
                expected = rank >= highest
                assert bool(native.highest(count, rank)) == expected, (
                    f"{count}-row table: rank {rank} must " + ("be capped" if expected else "remain promotable"))
                checks += 1
                assert native.clampRank(count, rank) == min(highest, max(0, rank)), (
                    f"{count}-row table: admin rank {rank} must use the table's range")
                checks += 1
        print(f"{checks} standalone faction rank predicate/admin checks passed", flush=True)
        run_lua(read(RECRUITER), native.highest)


if __name__ == "__main__":
    main()
