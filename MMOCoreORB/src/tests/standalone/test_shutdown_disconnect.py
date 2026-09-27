#!/usr/bin/env python3
"""Exercise production shutdown session traversal and completion diagnostics.

Requires Python 3 and a C++17 compiler (CXX or g++). Extracts disconnectAllPlayers
and the server's bounded disconnect wait into standard-library mocks. No Core3
or engine3 headers, libraries, components, or executable are built or run.
Temporary files stay under bin and are deleted on exit. --source-head exercises
the current commit, providing a regression baseline before this fix is committed.

Limits: the mock iterator detects map changes explicitly; it does not reproduce
engine hash iteration internals or rely on undefined iterator behavior. Session
references use shared_ptr, and locks/callbacks are deterministic test doubles.
These checks do not establish real concurrency, transport packet delivery,
engine reference semantics, database persistence, or complete runtime shutdown.
"""

import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile


CORE_ROOT = Path(__file__).resolve().parents[3]
PLAYER_PATH = Path("src/server/zone/managers/player/PlayerManagerImplementation.cpp")
SERVER_PATH = Path("src/server/ServerCore.cpp")


def extract_disconnect(source):
    start = source.index("void PlayerManagerImplementation::disconnectAllPlayers() {")
    end = source.index("\nbool PlayerManagerImplementation::", start)
    return source[start:end]


def extract_wait(source):
    disconnect = source.index("playerManager->disconnectAllPlayers();")
    start = source.index("int count = 0;", disconnect)
    end = source.index("\n\t\t}\n\t}", start)
    return "void ServerCore::waitForDisconnect() {\n" + source[start:end] + "\n}\n"


MOCKS = r'''
#include <algorithm>
#include <functional>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

using uint32 = unsigned int;
using uint64 = unsigned long long;
const char* commas = "";
void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
template <typename T> struct Reference {
    std::shared_ptr<std::remove_pointer_t<T>> value;
    Reference(std::nullptr_t = nullptr) {}
    Reference(std::shared_ptr<std::remove_pointer_t<T>> value) : value(value) {}
    operator T() const { return value.get(); }
    T operator->() const { return value.get(); }
};
template <typename T> using ManagedReference = T;
template <typename T> struct Vector : std::vector<T> {
    int size() const { return static_cast<int>(std::vector<T>::size()); }
    T get(int index) const { return this->at(index); }
    void add(T value) { this->push_back(value); }
};
struct Mutex { int depth = 0; };
struct CreatureObject;
struct PlayerObject;
struct ZoneClientSession { CreatureObject* player = nullptr; CreatureObject* getPlayer() { return player; } };
struct CreatureObject {
    ZoneClientSession* client = nullptr;
    PlayerObject* ghost = nullptr;
    int lockDepth = 0;
    PlayerObject* getPlayerObject() { return ghost; }
    ZoneClientSession* getClient() { return client; }
};
struct Locker {
    int& depth;
    explicit Locker(Mutex* mutex) : depth(mutex->depth) { ++depth; }
    explicit Locker(CreatureObject* player) : depth(player->lockDepth) { ++depth; }
    ~Locker() { --depth; }
};
struct PlayerObject {
    CreatureObject* player = nullptr;
    int disconnected = 0, linkDead = 0;
    std::function<void()> callback;
    void setLinkDead(bool safe) { require(safe, "safe logout flag lost"); ++linkDead; }
    void disconnect(bool close, bool lock) {
        require(close && lock && player->lockDepth > 0, "disconnect flags/locking changed");
        require(linkDead > disconnected, "disconnect occurred before link-dead transition");
        ++disconnected;
        if (callback) callback();
    }
};
template <typename Key, typename Value> struct Map;
template <typename Key, typename Value> struct HashTableIterator {
    Map<Key, Value>& map;
    unsigned generation;
    std::size_t position = 0;
    bool hasNext() const {
        require(generation == map.generation, "online map changed during traversal");
        return position < map.entries.size();
    }
    Value next() { require(hasNext(), "iterator exhausted"); return map.entries.at(position++).second; }
};
template <typename Key, typename Value> struct Map {
    std::vector<std::pair<Key, Value>> entries;
    unsigned generation = 0;
    int size() const { return static_cast<int>(entries.size()); }
    auto iterator() { return HashTableIterator<Key, Value>{*this, generation}; }
    void add(Key key, typename Value::value_type value) {
        for (auto& entry : entries) {
            if (entry.first == key) { entry.second.add(value); ++generation; return; }
        }
        Value values;
        values.add(value);
        entries.emplace_back(key, values);
        ++generation;
    }
    void remove(ZoneClientSession* session) {
        for (auto entry = entries.begin(); entry != entries.end(); ++entry) {
            auto& values = entry->second;
            const auto end = std::remove_if(values.begin(), values.end(),
                [&](auto value) { return static_cast<ZoneClientSession*>(value) == session; });
            if (end == values.end()) continue;
            values.erase(end, values.end());
            if (values.empty()) entries.erase(entry);
            ++generation; // Models both account erasure and replacement of its session vector.
            return;
        }
    }
    void clear() { entries.clear(); ++generation; }
};
struct Time { void updateToCurrentTime() {} int getTime() const { return 0; } };
struct Timer {
    void start() {}
    uint64 elapsedToNow() const { return 1000000000; }
    uint64 stopMs() const { return 1000; }
};
struct Math { template <typename T> static T max(T a, T b) { return std::max(a, b); } };
struct PlayerManagerImplementation {
    Mutex onlineMapMutex;
    Map<uint32, Vector<Reference<ZoneClientSession*>>> onlineZoneClientMap;
    std::ostringstream logs;
    std::ostream& info(bool) { return logs; }
    void disconnectAllPlayers();
};
struct Fixture {
    PlayerManagerImplementation manager;
    std::vector<std::unique_ptr<CreatureObject>> players;
    std::vector<std::unique_ptr<PlayerObject>> ghosts;
    std::vector<std::string> addresses;
    ZoneClientSession* add(uint32 account, const char* address = "shared-IP") {
        auto session = std::make_shared<ZoneClientSession>();
        players.push_back(std::make_unique<CreatureObject>());
        ghosts.push_back(std::make_unique<PlayerObject>());
        addresses.emplace_back(address); // Inputs only: production traversal must not group by IP.
        auto* player = players.back().get();
        auto* ghost = ghosts.back().get();
        player->client = session.get();
        player->ghost = ghost;
        session->player = player;
        ghost->player = player;
        ghost->callback = [this, client = session.get()] { manager.onlineZoneClientMap.remove(client); };
        manager.onlineZoneClientMap.add(account, Reference<ZoneClientSession*>(session));
        return session.get();
    }
    int disconnected() const {
        int count = 0;
        for (const auto& ghost : ghosts) count += ghost->disconnected;
        return count;
    }
};
struct Thread {
    inline static std::vector<int> sleeps;
    static void sleep(int delay) { sleeps.push_back(delay); }
};
struct ZoneServer { int remaining = 0; int getConnectionCount() const { return remaining; } };
struct ServerCore {
    ZoneServer* zoneServer;
    std::ostringstream logs, warnings;
    std::ostream& warning() { return warnings; }
    void info(const char* message, bool) { logs << message; }
    void waitForDisconnect();
};
'''

CASES = r'''
int main() {
    const char* names[] = {"empty map", "two accounts sharing an IP", "multiple sessions per account",
        "mixed account/IP sessions", "map lock released before callback", "null session",
        "session without player", "player without ghost", "replaced client remains connected",
        "snapshot survives map clearing", "logs count sessions rather than accounts",
        "client replacement during an earlier callback"};
    int failures = 0;
    for (int scenario = 0; scenario < 12; ++scenario) {
        Fixture fixture;
        auto& manager = fixture.manager;
        ZoneClientSession replacement;
        try {
            switch (scenario) {
            case 0: break;
            case 1:
                fixture.add(1); fixture.add(2);
                break;
            case 2:
                fixture.add(1); fixture.add(1); fixture.add(1);
                break;
            case 3:
                fixture.add(1); fixture.add(1); fixture.add(2, "other-IP"); fixture.add(3);
                break;
            case 4:
                fixture.add(1);
                fixture.ghosts[0]->callback = [&] {
                    require(manager.onlineMapMutex.depth == 0, "callback runs while map lock held");
                };
                break;
            case 5:
                manager.onlineZoneClientMap.add(1, nullptr);
                break;
            case 6:
                fixture.add(1)->player = nullptr;
                break;
            case 7:
                fixture.add(1)->player->ghost = nullptr;
                break;
            case 8:
                fixture.add(1)->player->client = &replacement;
                fixture.ghosts[0]->callback = nullptr;
                break;
            case 9:
                fixture.add(1); fixture.add(2); fixture.add(3);
                fixture.ghosts[0]->callback = [&] { manager.onlineZoneClientMap.clear(); };
                break;
            case 10:
                fixture.add(1); fixture.add(1); fixture.add(1); fixture.add(2);
                for (auto& ghost : fixture.ghosts) ghost->callback = nullptr;
                break;
            case 11:
                fixture.add(1); fixture.add(2);
                fixture.ghosts[0]->callback = [&] { fixture.players[1]->client = &replacement; };
                fixture.ghosts[1]->callback = nullptr;
                break;
            }
            manager.disconnectAllPlayers();
            const int expected[] = {0, 2, 3, 4, 1, 0, 0, 0, 0, 3, 4, 1};
            require(fixture.disconnected() == expected[scenario], "wrong sessions disconnected");
            for (const auto& ghost : fixture.ghosts)
                require(ghost->disconnected <= 1, "session disconnected more than once");
            if (scenario == 10)
                require(manager.logs.str().find("Disconnecting 4 player sessions.") != std::string::npos,
                        "initial log reports account count instead of session count");
            if (scenario >= 1 && scenario <= 3)
                require(manager.onlineZoneClientMap.size() == 0, "online sessions remain after callbacks");
            require(manager.onlineMapMutex.depth == 0, "map lock not released");
            for (const auto& player : fixture.players)
                require(player->lockDepth == 0, "player lock not released");
            std::cout << "PASS " << names[scenario] << '\n';
        } catch (const std::exception& error) {
            ++failures;
            std::cout << "FAIL " << names[scenario] << ": " << error.what() << '\n';
        }
    }
    for (int remaining : {0, 3}) {
        try {
            ZoneServer zone;
            zone.remaining = remaining;
            ServerCore server{&zone, {}, {}};
            Thread::sleeps.clear();
            server.waitForDisconnect();
            require(Thread::sleeps == std::vector<int>(remaining ? 20 : 0, 500), "disconnect wait changed");
            if (remaining) {
                require(server.logs.str().empty(), "timed-out wait reported success");
                require(server.warnings.str().find("3 players remain connected") != std::string::npos,
                        "missing timeout warning/count");
            } else {
                require(server.warnings.str().empty(), "completed disconnect warned");
                require(server.logs.str() == "All players disconnected", "missing completion message");
            }
            std::cout << "PASS disconnect wait: " << remaining << " remaining\n";
        } catch (const std::exception& error) {
            ++failures;
            std::cout << "FAIL disconnect wait: " << remaining << " remaining: " << error.what() << '\n';
        }
    }
    std::cout << 14 - failures << " passed, " << failures << " failed\n";
    return failures == 0 ? 0 : 1;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-head", action="store_true", help="exercise current HEAD instead of working source")
    args = parser.parse_args()

    def read(path):
        if args.source_head:
            return subprocess.run(["git", "show", f"HEAD:MMOCoreORB/{path.as_posix()}"],
                                  cwd=CORE_ROOT, check=True, capture_output=True, text=True).stdout
        return (CORE_ROOT / path).read_text()

    program = MOCKS + extract_disconnect(read(PLAYER_PATH)) + extract_wait(read(SERVER_PATH)) + CASES
    compiler = shlex.split(os.environ.get("CXX", "g++"))
    with tempfile.TemporaryDirectory(prefix=".shutdown-disconnect-test-", dir=CORE_ROOT / "bin") as temporary:
        directory = Path(temporary)
        source, executable = directory / "test.cpp", directory / "test"
        source.write_text(program)
        subprocess.run([*compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic",
                        str(source), "-o", str(executable)], check=True, timeout=30)
        print("Source: current HEAD" if args.source_head else "Source: working tree", flush=True)
        return subprocess.run([str(executable)], timeout=10).returncode


if __name__ == "__main__":
    raise SystemExit(main())
