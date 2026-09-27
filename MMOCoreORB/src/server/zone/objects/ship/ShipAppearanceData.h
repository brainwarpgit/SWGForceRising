#ifndef SHIPAPPEARANCEDATA_H_
#define SHIPAPPEARANCEDATA_H_

#include "engine/engine.h"
#include "templates/datatables/DataTableIff.h"
#include "templates/datatables/DataTableRow.h"
#include "server/zone/objects/ship/ComponentSlots.h"

class DataTableRow;

class ShipAppearanceData : public Object {
protected:
	HashTable<String, String> appearanceMap;
	HashTable<uint32, String> advancedMap;
	HashTable<uint32, String> defaultMap;

	String dataName;

public:
	ShipAppearanceData(const String& chassisName) {
		dataName = chassisName;
	}

	void readChassisData(const DataTableIff& dataTable) {
		// Some client tables omit unused slots. Column positions therefore do
		// not necessarily match the component-slot enumeration.
		Vector<int> columnSlots;

		for (int column = 0; column < dataTable.getTotalColumns(); ++column) {
			int slot = -1;
			const auto& columnName = dataTable.getColumnNameByIndex(column);

			for (int candidate = 0; candidate <= Components::CAPITALSLOTMAX; ++candidate) {
				if (columnName == Components::shipComponentSlotToString(candidate)) {
					slot = candidate;
					break;
				}
			}

			columnSlots.add(slot);
		}

		for (int i = 0; i < dataTable.getTotalRows(); ++i) {
			const DataTableRow* row = dataTable.getRow(i);
			if (row == nullptr || row->getCellsSize() == 0) {
				break;
			}

			int slot = -1;
			String key;
			String value;

			for (int i = 0; i < row->getCellsSize(); ++i) {
				auto cell = row->getCell(i);
				if (cell == nullptr || cell->toString() == "") {
					continue;
				}

				if (i == 0) {
					key = cell->toString();
				} else {
					slot = columnSlots.get(i);

					if (slot == -1) {
						continue;
					}

					value = cell->toString();
					break;
				}
			}

			if (slot != -1 && key != "" && value != "") {
				if (defaultMap.get(slot) == "" && !value.contains("_s02")) {
					defaultMap.put(slot, key);
				}

				if (advancedMap.get(slot) == "" && value.contains("_s02")) {
					advancedMap.put(slot, key);
				}

				appearanceMap.put(key, value);
			}
		}
	}

	const String& getDefaultAppearance(uint32 slot) const {
		return defaultMap.get(slot);
	}

	const String& getAdvancedAppearance(uint32 slot) const {
		return advancedMap.get(slot);
	}

	bool contains(const String& dataName) const {
		return appearanceMap.get(dataName) != "";
	}

	int size() const {
		return appearanceMap.size();
	}
};

#endif // SHIPAPPEARANCEDATA_H_
