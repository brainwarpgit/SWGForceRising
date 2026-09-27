#ifndef SKILLSURRENDERPLAN_H_
#define SKILLSURRENDERPLAN_H_

#include <cstddef>
#include <map>
#include <set>
#include <string>
#include <vector>

// Dependency planning only. The caller supplies surrender eligibility, checks
// gameplay restrictions, and performs the resulting removals under its lock.
namespace SkillSurrenderPlan {

struct Node {
	std::string name;
	std::vector<std::string> required;
	bool eligible;
};

struct Result {
	std::vector<std::string> skills;
	std::string error;
};

inline Result build(const std::vector<Node>& owned, const std::string& root, bool all) {
	std::map<std::string, std::size_t> indices;
	for (std::size_t i = 0; i < owned.size(); ++i) {
		if (owned[i].name.empty() || !indices.emplace(owned[i].name, i).second)
			return {{}, "The owned skill list contains an empty or duplicate skill name."};
	}

	std::vector<std::set<std::size_t>> required(owned.size()), dependents(owned.size());
	for (std::size_t i = 0; i < owned.size(); ++i) {
		for (const auto& name : owned[i].required) {
			auto found = indices.find(name);
			if (found != indices.end()) {
				required[i].insert(found->second);
				dependents[found->second].insert(i);
			}
		}
	}

	std::vector<bool> selected(owned.size(), false);
	std::vector<std::size_t> pending;
	if (all) {
		// Retain every prerequisite, including transitive prerequisites, of a
		// protected skill. The remaining eligible subset can be removed safely.
		for (std::size_t i = 0; i < owned.size(); ++i) {
			selected[i] = owned[i].eligible;
			if (!selected[i])
				pending.push_back(i);
		}
		for (std::size_t cursor = 0; cursor < pending.size(); ++cursor) {
			for (auto prerequisite : required[pending[cursor]]) {
				if (selected[prerequisite]) {
					selected[prerequisite] = false;
					pending.push_back(prerequisite);
				}
			}
		}
	} else {
		auto found = indices.find(root);
		if (found == indices.end())
			return {{}, "You do not have the selected skill."};
		if (!owned[found->second].eligible)
			return {{}, "The selected skill cannot be surrendered."};

		selected[found->second] = true;
		pending.push_back(found->second);
		for (std::size_t cursor = 0; cursor < pending.size(); ++cursor) {
			for (auto dependent : dependents[pending[cursor]]) {
				if (!owned[dependent].eligible)
					return {{}, "A skill that cannot be surrendered requires the selected skill."};
				if (!selected[dependent]) {
					selected[dependent] = true;
					pending.push_back(dependent);
				}
			}
		}
	}

	// Remove dependents before their prerequisites. Resolve ties by name so
	// confirmation and execution agree even if the owned list changes order.
	std::vector<std::size_t> remainingDependents(owned.size(), 0);
	std::set<std::string> ready;
	std::size_t selectedCount = 0;
	for (std::size_t i = 0; i < owned.size(); ++i) {
		if (!selected[i])
			continue;
		++selectedCount;
		for (auto dependent : dependents[i]) {
			if (selected[dependent])
				++remainingDependents[i];
		}
		if (remainingDependents[i] == 0)
			ready.insert(owned[i].name);
	}

	Result result;
	while (!ready.empty()) {
		auto i = indices.find(*ready.begin())->second;
		result.skills.push_back(owned[i].name);
		ready.erase(ready.begin());
		for (auto prerequisite : required[i]) {
			if (selected[prerequisite] && --remainingDependents[prerequisite] == 0)
				ready.insert(owned[prerequisite].name);
		}
	}
	if (result.skills.size() != selectedCount)
		return {{}, "The selected skills have circular prerequisites and cannot be surrendered safely."};
	return result;
}

} // namespace SkillSurrenderPlan

#endif // SKILLSURRENDERPLAN_H_
