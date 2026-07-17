"""Каталог Арсенала Империи (~95 предметов)."""

from __future__ import annotations

RARITY_ORDER = ("common", "uncommon", "rare", "epic", "legendary", "mythic")

RARITY_LABEL = {
    "common": "Обычный",
    "uncommon": "Необычный",
    "rare": "Редкий",
    "epic": "Эпический",
    "legendary": "Легендарный",
    "mythic": "Мифический",
}

RARITY_MARK = {
    "common": "⬜",
    "uncommon": "🟩",
    "rare": "🟦",
    "epic": "🟪",
    "legendary": "🟨",
    "mythic": "🟥",
}

SELL_PRICE = {
    "common": 15,
    "uncommon": 40,
    "rare": 120,
    "epic": 350,
    "legendary": 900,
    "mythic": 2500,
}

DONATE_TREASURY = {
    "epic": 200,
    "legendary": 600,
    "mythic": 1500,
}

SLOTS = ("tool", "weapon", "relic")
SLOT_LABEL = {"tool": "Инструмент", "weapon": "Оружие", "relic": "Реликвия"}


def _i(
    id: str,
    name: str,
    rarity: str,
    slot: str,
    family: str,
    pools: list[str],
    *,
    passives: dict | None = None,
    charge: dict | None = None,
    aura: dict | None = None,
    desc: str = "",
) -> dict:
    return {
        "id": id,
        "name": name,
        "rarity": rarity,
        "slot": slot,
        "family": family,
        "pools": pools,
        "passives": passives or {},
        "charge": charge,
        "aura": aura,
        "desc": desc,
    }


ITEMS: dict[str, dict] = {}


def _reg(*items: dict) -> None:
    for it in items:
        ITEMS[it["id"]] = it


# --- Шахта (mine) ---
_reg(
    _i("rusty_pick", "Ржавая кирка", "common", "tool", "vein", ["mine"], passives={"job_bonus": {"mine": 0.03}}, desc="+3% к шахте"),
    _i("dusty_lamp", "Пыльная лампа", "common", "tool", "vein", ["mine"], passives={"job_bonus": {"mine": 0.02}}, desc="+2% к шахте"),
    _i("scrap_helmet", "Каска с царапиной", "common", "relic", "vein", ["mine"], passives={"work_mult": 0.02}, desc="+2% ко всем работам"),
    _i("ore_pebble", "Самородок-галечка", "common", "relic", "vein", ["mine"], passives={"job_bonus": {"mine": 0.04}}, desc="+4% к шахте"),
    _i("mine_gloves", "Перчатки забоя", "common", "tool", "vein", ["mine"], passives={"job_bonus": {"mine": 0.03}}, desc="+3% к шахте"),
    _i("tin_bucket", "Оловянное ведро", "common", "tool", "vein", ["mine"], passives={"job_bonus": {"mine": 0.02}}, desc="+2% к шахте"),
    _i("copper_pick", "Медная кирка", "uncommon", "tool", "vein", ["mine"], passives={"job_bonus": {"mine": 0.06}}, desc="+6% к шахте"),
    _i("glow_lamp", "Лампа рудокопа", "uncommon", "tool", "vein", ["mine"], passives={"job_bonus": {"mine": 0.05}, "loot_luck": 0.01}, desc="+5% шахта, чуть удачи лута"),
    _i("iron_helmet", "Железная каска", "uncommon", "relic", "vein", ["mine"], passives={"work_mult": 0.04}, desc="+4% ко всем работам"),
    _i("vein_shard", "Осколок жилы", "uncommon", "relic", "vein", ["mine"], passives={"job_bonus": {"mine": 0.07}}, desc="+7% к шахте"),
    _i("deep_pick", "Кирка глубин", "rare", "tool", "vein", ["mine"], passives={"job_bonus": {"mine": 0.10}}, desc="+10% к шахте"),
    _i("echo_lamp", "Лампа Глубин", "rare", "tool", "vein", ["mine"], passives={"job_bonus": {"mine": 0.08}, "loot_luck": 0.02}, desc="+8% шахта, +удача"),
    _i("ore_eye", "Самородный глаз", "rare", "relic", "vein", ["mine"], passives={"job_bonus": {"mine": 0.12}}, desc="+12% к шахте"),
    _i("echo_pick", "Кирка Глубинного Эха", "epic", "tool", "vein", ["mine"], passives={"job_bonus": {"mine": 0.15}, "loot_luck": 0.03}, desc="+15% шахта"),
    _i("heart_vein", "Сердце Жилы", "legendary", "relic", "vein", ["mine"],
       passives={"job_bonus": {"mine": 0.08}},
       charge={"code": "free_mine_x2", "cooldown_hours": 24},
       desc="Раз в сутки: шахта без КД и ×2 крон"),
)

# --- Рынок (market) ---
_reg(
    _i("wood_scales", "Деревянные весы", "common", "tool", "trade", ["market"], passives={"job_bonus": {"market": 0.03}}, desc="+3% к рынку"),
    _i("cloth_bag", "Торговый мешок", "common", "tool", "trade", ["market"], passives={"job_bonus": {"market": 0.02}}, desc="+2% к рынку"),
    _i("chalk_mark", "Меловая бирка", "common", "relic", "trade", ["market"], passives={"tax_add": -0.01}, desc="−1 п.п. налога с работ"),
    _i("rusty_seal", "Ржавая печать", "common", "relic", "trade", ["market"], passives={"job_bonus": {"market": 0.03}}, desc="+3% к рынку"),
    _i("coin_pouch", "Кошелёк торговца", "common", "tool", "trade", ["market"], passives={"job_bonus": {"market": 0.04}}, desc="+4% к рынку"),
    _i("market_apron", "Фартук рынка", "common", "relic", "trade", ["market"], passives={"work_mult": 0.02}, desc="+2% ко всем работам"),
    _i("brass_scales", "Латунные весы", "uncommon", "tool", "trade", ["market"], passives={"job_bonus": {"market": 0.06}}, desc="+6% к рынку"),
    _i("guild_seal", "Печать гильдии", "uncommon", "relic", "trade", ["market"], passives={"tax_add": -0.02, "job_bonus": {"market": 0.04}}, desc="−2 п.п. налога, +4% рынок"),
    _i("silk_bag", "Шёлковый мешок", "uncommon", "tool", "trade", ["market"], passives={"job_bonus": {"market": 0.07}}, desc="+7% к рынку"),
    _i("merchant_ring", "Кольцо купца", "uncommon", "relic", "trade", ["market"], passives={"job_bonus": {"market": 0.05}, "work_mult": 0.02}, desc="+5% рынок"),
    _i("gold_scales", "Золотые весы", "rare", "tool", "trade", ["market"], passives={"job_bonus": {"market": 0.10}}, desc="+10% к рынку"),
    _i("false_seal", "Ложная печать", "rare", "relic", "trade", ["market"], passives={"tax_add": -0.03, "job_bonus": {"market": 0.06}}, desc="−3 п.п. налога"),
    _i("ledger_quill", "Перо бухгалтера", "rare", "tool", "trade", ["market"], passives={"job_bonus": {"market": 0.11}}, desc="+11% к рынку"),
    _i("caravan_charm", "Амулет каравана", "epic", "relic", "trade", ["market"], passives={"job_bonus": {"market": 0.14}, "tax_add": -0.02}, desc="+14% рынок"),
    _i("guild_ring", "Перстень Гильдии", "legendary", "relic", "trade", ["market"],
       passives={"job_bonus": {"market": 0.06}},
       charge={"code": "no_tax_3", "cooldown_hours": 48},
       desc="3 работы подряд без налога (КД 48ч)"),
)

# --- Охрана (guard) ---
_reg(
    _i("wood_shield", "Деревянный щит", "common", "weapon", "guard", ["guard"], passives={"job_bonus": {"guard": 0.03}}, desc="+3% к охране"),
    _i("patrol_whistle", "Свисток дозора", "common", "tool", "guard", ["guard"], passives={"job_bonus": {"guard": 0.02}, "treasury_bonus_add": 2}, desc="+2 к взносу в казну"),
    _i("leather_cloak", "Кожаный плащ", "common", "relic", "guard", ["guard"], passives={"job_bonus": {"guard": 0.03}}, desc="+3% к охране"),
    _i("iron_badge", "Железный жетон", "common", "relic", "guard", ["guard"], passives={"work_mult": 0.02}, desc="+2% ко всем работам"),
    _i("short_spear", "Короткое копьё", "common", "weapon", "guard", ["guard"], passives={"job_bonus": {"guard": 0.04}}, desc="+4% к охране"),
    _i("night_lantern", "Фонарь караула", "common", "tool", "guard", ["guard"], passives={"job_bonus": {"guard": 0.02}}, desc="+2% к охране"),
    _i("bronze_shield", "Бронзовый щит", "uncommon", "weapon", "guard", ["guard"], passives={"job_bonus": {"guard": 0.06}}, desc="+6% к охране"),
    _i("command_seal", "Печать коменданта", "uncommon", "relic", "guard", ["guard"], passives={"job_bonus": {"guard": 0.05}, "treasury_bonus_add": 5}, desc="+5 в казну при успехе"),
    _i("watch_cloak", "Плащ дозора", "uncommon", "relic", "guard", ["guard"], passives={"job_bonus": {"guard": 0.07}}, desc="+7% к охране"),
    _i("steel_spear", "Стальное копьё", "uncommon", "weapon", "guard", ["guard"], passives={"job_bonus": {"guard": 0.06}, "raid_mult": 0.02}, desc="+6% охрана, +2% рейд"),
    _i("tower_shield", "Башенный щит", "rare", "weapon", "guard", ["guard"], passives={"job_bonus": {"guard": 0.10}, "raid_defend": 0.05}, desc="+10% охрана, −5% урон рейда по стране"),
    _i("vigil_cloak", "Плащ бдения", "rare", "relic", "guard", ["guard"], passives={"job_bonus": {"guard": 0.09}, "treasury_bonus_add": 8}, desc="+9% охрана"),
    _i("captain_badge", "Значок капитана", "rare", "relic", "guard", ["guard"], passives={"job_bonus": {"guard": 0.08}, "work_mult": 0.03}, desc="+8% охрана"),
    _i("aegis_plate", "Эгида Стражи", "epic", "weapon", "guard", ["guard"], passives={"job_bonus": {"guard": 0.14}, "raid_defend": 0.08}, desc="+14% охрана, защита казны"),
    _i("sleepless_cloak", "Плащ Неусыпного", "legendary", "relic", "guard", ["guard"],
       passives={"job_bonus": {"guard": 0.08}},
       charge={"code": "full_energy_guard", "cooldown_hours": 12},
       desc="При успехе охраны: полная энергия (КД 12ч)"),
)

# --- Тень / контрабанда (shadow) ---
_reg(
    _i("bent_lockpick", "Кривая отмычка", "common", "tool", "shadow", ["smuggle"], passives={"smuggle_chance": 0.02}, desc="+2% шанс контрабанды"),
    _i("dark_sack", "Тёмный мешок", "common", "tool", "shadow", ["smuggle"], passives={"smuggle_reward": 0.05}, desc="+5% награды контрабанды"),
    _i("fake_pass", "Поддельный пропуск", "common", "relic", "shadow", ["smuggle"], passives={"jail_hours_mult": 0.9}, desc="Тюрьма −10% времени"),
    _i("ash_mask", "Маска из золы", "common", "relic", "shadow", ["smuggle"], passives={"smuggle_chance": 0.03}, desc="+3% шанс контрабанды"),
    _i("silent_boots", "Тихие сапоги", "common", "tool", "shadow", ["smuggle"], passives={"smuggle_chance": 0.02, "smuggle_fine_mult": 0.9}, desc="Штраф −10%"),
    _i("smoke_vial", "Флакон дыма", "common", "relic", "shadow", ["smuggle", "cursed"], passives={"smuggle_chance": 0.04}, desc="+4% шанс"),
    _i("silver_lockpick", "Серебряная отмычка", "uncommon", "tool", "shadow", ["smuggle"], passives={"smuggle_chance": 0.05}, desc="+5% шанс контрабанды"),
    _i("shadow_cloak", "Плащ тени", "uncommon", "relic", "shadow", ["smuggle"], passives={"smuggle_chance": 0.04, "jail_hours_mult": 0.85}, desc="+шанс, короче тюрьма"),
    _i("forged_papers", "Липовые бумаги", "uncommon", "relic", "shadow", ["smuggle"], passives={"smuggle_chance": 0.05, "smuggle_fine_mult": 0.85}, desc="+шанс, меньше штраф"),
    _i("night_sack", "Ночной мешок", "uncommon", "tool", "shadow", ["smuggle"], passives={"smuggle_reward": 0.10, "smuggle_chance": 0.03}, desc="+награда"),
    _i("master_pick", "Отмычка мастера", "rare", "tool", "shadow", ["smuggle"], passives={"smuggle_chance": 0.08}, desc="+8% шанс"),
    _i("ghost_pass", "Призрачный паспорт", "rare", "relic", "shadow", ["smuggle"], passives={"smuggle_chance": 0.06, "jail_hours_mult": 0.7}, desc="Тюрьма −30%"),
    _i("void_mask", "Маска пустоты", "rare", "relic", "shadow", ["smuggle", "cursed"], passives={"smuggle_chance": 0.07, "raid_mult": -0.03}, desc="+шанс, −3% рейд"),
    _i("black_mark", "Чёрная метка", "epic", "relic", "shadow", ["smuggle", "cursed"],
       passives={"smuggle_chance": 0.10, "smuggle_reward": 0.15, "raid_defend": -0.10},
       desc="+контрабанда, по тебе рейды сильнее на 10%"),
    _i("black_sack", "Чёрный мешок", "legendary", "tool", "shadow", ["smuggle"],
       passives={"smuggle_chance": 0.05},
       charge={"code": "smuggle_no_jail", "cooldown_hours": 24},
       desc="Раз в сутки: провал без тюрьмы (только штраф)"),
)

# --- Рейд (raid / weapon) ---
_reg(
    _i("notched_blade", "Зубчатый клинок", "common", "weapon", "raid", ["raid", "guard"], passives={"raid_mult": 0.03}, desc="+3% к рейду"),
    _i("war_horn", "Рог налёта", "common", "relic", "raid", ["raid"], passives={"raid_mult": 0.02}, desc="+2% к рейду"),
    _i("raid_bannerette", "Маленькое знамя", "common", "weapon", "raid", ["raid"], passives={"raid_mult": 0.03}, desc="+3% к рейду"),
    _i("loot_sack", "Мешок добычи", "common", "tool", "raid", ["raid"], passives={"raid_leader_share": 0.02}, desc="+2 п.п. доли лидера"),
    _i("spike_gauntlet", "Шипованная рукавица", "common", "weapon", "raid", ["raid", "guard"], passives={"raid_mult": 0.02, "job_bonus": {"guard": 0.02}}, desc="+рейд и охрана"),
    _i("ash_banner", "Пепельное знамя", "common", "weapon", "raid", ["raid"], passives={"raid_mult": 0.04}, desc="+4% к рейду"),
    _i("steel_blade", "Стальной клинок", "uncommon", "weapon", "raid", ["raid", "guard"], passives={"raid_mult": 0.05}, desc="+5% к рейду"),
    _i("war_drum", "Барабан войны", "uncommon", "relic", "raid", ["raid"], passives={"raid_mult": 0.04, "raid_cd_hours": -0.25}, desc="+4% рейд, −15 мин КД"),
    _i("crimson_pennant", "Багровый вымпел", "uncommon", "weapon", "raid", ["raid"], passives={"raid_mult": 0.06}, desc="+6% к рейду"),
    _i("captain_horn", "Рог капитана", "uncommon", "relic", "raid", ["raid"], passives={"raid_mult": 0.05, "raid_leader_share": 0.03}, desc="+рейд и доля лидера"),
    _i("raider_saber", "Сабля налётчика", "rare", "weapon", "raid", ["raid"], passives={"raid_mult": 0.09}, desc="+9% к рейду"),
    _i("blood_banner", "Кровавое знамя", "rare", "weapon", "raid", ["raid"], passives={"raid_mult": 0.08, "raid_cd_hours": -0.5}, desc="+8% рейд, −30 мин КД"),
    _i("siege_charm", "Амулет осады", "rare", "relic", "raid", ["raid"], passives={"raid_mult": 0.07, "raid_leader_share": 0.05}, desc="+7% рейд"),
    _i("crimson_banner", "Знамя Багрового Дозора", "epic", "weapon", "raid", ["raid"],
       passives={"raid_mult": 0.12},
       charge={"code": "war_score_bonus", "cooldown_hours": 6},
       desc="+12% рейд; заряд: +2 очка войны бесед"),
    _i("empire_blade", "Клинок Имперского Налёта", "legendary", "weapon", "raid", ["raid"],
       passives={"raid_mult": 0.10},
       charge={"code": "raid_cd_minus_1h", "cooldown_hours": 24},
       desc="+10% рейд; заряд: КД рейда −1ч"),
    _i("throne_shard", "Осколок Трона", "legendary", "relic", "raid", ["raid", "guard"],
       passives={"raid_defend": 0.05},
       charge={"code": "raid_reflect", "cooldown_hours": 48},
       desc="При рейде по тебе: шанс отразить часть добычи"),
)

# --- Регалии / смешанные ---
_reg(
    _i("wood_seal", "Деревянная печать", "common", "relic", "regalia", ["mine", "market", "guard"], passives={"work_mult": 0.02}, desc="+2% работы"),
    _i("ink_pot", "Чернильница писца", "common", "tool", "regalia", ["market"], passives={"quest_luck": 0.05}, desc="Чуть быстрее квест (флейвор)"),
    _i("citizen_badge", "Жетон гражданина", "common", "relic", "regalia", ["guard", "market"], passives={"work_mult": 0.03}, desc="+3% работы"),
    _i("chat_ribbon", "Лента беседы", "common", "relic", "regalia", ["mine", "market"], passives={"work_mult": 0.02}, desc="+2% работы"),
    _i("bronze_crest", "Бронзовый герб", "uncommon", "relic", "regalia", ["guard", "raid"], passives={"work_mult": 0.04, "raid_mult": 0.02}, desc="+работы и рейд"),
    _i("senate_token", "Жетон сената", "uncommon", "relic", "regalia", ["market", "guard"], passives={"tax_add": -0.01, "work_mult": 0.03}, desc="−налог, +работы"),
    _i("chronicle_quill", "Перо летописца", "uncommon", "tool", "regalia", ["market"], passives={"work_mult": 0.04}, desc="+4% работы"),
    _i("silver_crest", "Серебряный герб", "rare", "relic", "regalia", ["raid", "guard"], passives={"work_mult": 0.05, "raid_mult": 0.04}, desc="+работы и рейд"),
    _i("law_scroll", "Свиток законов", "rare", "relic", "regalia", ["market"], passives={"tax_add": -0.02, "work_mult": 0.05}, desc="−налог"),
    _i("empire_seal", "Печать Империи", "epic", "relic", "regalia", ["mine", "market", "guard"], passives={"work_mult": 0.10}, desc="+10% ко всем работам"),
    _i("senate_seal", "Печать беседного сената", "legendary", "relic", "regalia", ["market", "guard"],
       passives={"work_mult": 0.05},
       charge={"code": "tax_override_week", "cooldown_hours": 168},
       desc="Лидер: смена налога вне КД оформления (раз в неделю)"),
    _i("quest_cup", "Кубок Летописца", "legendary", "relic", "regalia", ["mine", "market", "guard"],
       passives={"work_mult": 0.04},
       charge={"code": "quest_x2", "cooldown_hours": 24},
       desc="Раз в сутки: работа считает ×2 к прогрессу квеста"),
)

# --- Сезонные / cursed ---
_reg(
    _i("plague_mask", "Маска чумного доктора", "rare", "relic", "season", ["cursed", "guard"],
       passives={"work_mult": 0.05},
       charge={"code": "ignore_plague", "cooldown_hours": 24},
       desc="Игнор штрафа чумы на сутки (заряд)"),
    _i("raid_torch", "Факел ночного марша", "rare", "weapon", "season", ["raid"],
       passives={"raid_mult": 0.06, "raid_cd_hours": -0.5},
       desc="+рейд, короче КД"),
    _i("cursed_coin", "Проклятая монета", "epic", "relic", "season", ["cursed", "smuggle"],
       passives={"smuggle_chance": 0.08, "work_mult": -0.05, "smuggle_reward": 0.20},
       desc="+контрабанда, −5% работы"),
    _i("bear_collar", "Ошейник медведя-герба", "uncommon", "relic", "regalia", ["guard", "raid"],
       passives={"raid_mult": 0.03, "job_bonus": {"guard": 0.04}},
       desc="Для стран с 🐻"),
)

# --- Ещё common/uncommon чтобы добрать ~95 ---
_reg(
    _i("flint_chip", "Кремень", "common", "tool", "vein", ["mine"], passives={"job_bonus": {"mine": 0.02}}, desc="+2% шахта"),
    _i("rope_coil", "Моток верёвки", "common", "tool", "vein", ["mine"], passives={"job_bonus": {"mine": 0.02}}, desc="+2% шахта"),
    _i("salt_bag", "Мешок соли", "common", "tool", "trade", ["market"], passives={"job_bonus": {"market": 0.02}}, desc="+2% рынок"),
    _i("price_tag", "Ценник", "common", "relic", "trade", ["market"], passives={"job_bonus": {"market": 0.02}}, desc="+2% рынок"),
    _i("guard_belt", "Ремень стража", "common", "tool", "guard", ["guard"], passives={"job_bonus": {"guard": 0.02}}, desc="+2% охрана"),
    _i("dull_dagger", "Тупой кинжал", "common", "weapon", "raid", ["raid"], passives={"raid_mult": 0.02}, desc="+2% рейд"),
    _i("smoke_pouch", "Кисет дыма", "common", "tool", "shadow", ["smuggle"], passives={"smuggle_chance": 0.02}, desc="+2% контрабанда"),
    _i("tin_crest", "Оловянный герб", "common", "relic", "regalia", ["mine", "guard"], passives={"work_mult": 0.01}, desc="+1% работы"),
    _i("polished_pick", "Полированная кирка", "uncommon", "tool", "vein", ["mine"], passives={"job_bonus": {"mine": 0.05}}, desc="+5% шахта"),
    _i("trade_ledger", "Книга учёта", "uncommon", "tool", "trade", ["market"], passives={"job_bonus": {"market": 0.05}, "tax_add": -0.01}, desc="+рынок, −налог"),
    _i("iron_whistle", "Железный свисток", "uncommon", "tool", "guard", ["guard"], passives={"job_bonus": {"guard": 0.05}, "treasury_bonus_add": 3}, desc="+охрана"),
    _i("shadow_dagger", "Теневой кинжал", "uncommon", "weapon", "shadow", ["smuggle", "raid"], passives={"smuggle_chance": 0.03, "raid_mult": 0.03}, desc="+тень и рейд"),
    _i("war_charm", "Амулет войны", "uncommon", "relic", "raid", ["raid"], passives={"raid_mult": 0.04}, desc="+4% рейд"),
    _i("citizen_charm", "Амулет гражданина", "uncommon", "relic", "regalia", ["mine", "market", "guard"], passives={"work_mult": 0.03}, desc="+3% работы"),
    _i("deep_ore", "Глубинная руда", "rare", "relic", "vein", ["mine"], passives={"job_bonus": {"mine": 0.09}, "loot_luck": 0.02}, desc="+9% шахта"),
    _i("market_crown", "Венок рынка", "rare", "relic", "trade", ["market"], passives={"job_bonus": {"market": 0.09}, "tax_add": -0.02}, desc="+рынок"),
    _i("sentinel_helm", "Шлем часового", "rare", "relic", "guard", ["guard"], passives={"job_bonus": {"guard": 0.10}, "raid_defend": 0.03}, desc="+охрана"),
    _i("raid_cloak", "Плащ налёта", "rare", "relic", "raid", ["raid"], passives={"raid_mult": 0.08}, desc="+8% рейд"),
    _i("shadow_amulet", "Амулет тени", "rare", "relic", "shadow", ["smuggle"], passives={"smuggle_chance": 0.07, "smuggle_reward": 0.08}, desc="+контрабанда"),
    _i("empire_ink", "Чернила Империи", "epic", "tool", "regalia", ["market", "mine"], passives={"work_mult": 0.08}, desc="+8% работы"),
    _i("vault_key", "Ключ казны", "epic", "relic", "regalia", ["guard", "market"], passives={"treasury_bonus_add": 15, "work_mult": 0.05}, desc="+казне и работы"),
    _i("storm_blade", "Клинок бури", "epic", "weapon", "raid", ["raid"], passives={"raid_mult": 0.11, "raid_cd_hours": -0.5}, desc="+11% рейд"),
)

# --- Мифические (6) ---
_reg(
    _i("dawn_crown", "Корона Рассвета", "mythic", "relic", "mythic", ["raid", "guard", "mine"],
       passives={"work_mult": 0.05},
       aura={"nation_work_mult": 0.10, "raid_target_mark": True},
       charge={"code": "announce_mythic", "cooldown_hours": 168},
       desc="Аура: граждане страны +10% к работам. Страна — лакомая цель."),
    _i("empire_heart", "Сердце Империи", "mythic", "relic", "mythic", ["market", "guard"],
       passives={"work_mult": 0.06},
       aura={"nation_treasury_raid_defend": 0.08},
       charge={"code": "treasury_convert", "cooldown_hours": 168},
       desc="Аура: казна страны крепче. Заряд: личный→казна ×1.5 до 500."),
    _i("eternal_night_blade", "Клинок Вечной Ночи", "mythic", "weapon", "mythic", ["raid"],
       passives={"raid_mult": 0.12},
       charge={"code": "raid_night_once", "cooldown_hours": 72},
       desc="Заряд: 1 рейд с КД как в ночь рейдов (15 мин)."),
    _i("fate_scroll", "Свиток Переписывания Судеб", "mythic", "relic", "mythic", ["market", "mine", "smuggle"],
       passives={"work_mult": 0.04},
       charge={"code": "reset_job_cds", "cooldown_hours": 168},
       desc="Заряд: сброс КД всех работ и контрабанды."),
    _i("nameless_shadow", "Тень Без Имени", "mythic", "tool", "mythic", ["smuggle"],
       passives={"smuggle_chance": 0.08, "smuggle_reward": 0.20},
       charge={"code": "shadow_stash", "cooldown_hours": 72},
       desc="Заряд после 3 успехов подряд: +300 в казну."),
    _i("first_day_torch", "Факел Первого Дня", "mythic", "weapon", "mythic", ["mine", "raid"],
       passives={"raid_mult": 0.05, "loot_luck": 0.05},
       aura={"personal_gold_vein": True},
       charge={"code": "announce_mythic", "cooldown_hours": 168},
       desc="Для тебя ивент всегда как золотая жила. Анонс при экипе."),
)

# --- Доп. легенды для ~12 ---
_reg(
    _i("double_vein_pick", "Кирка Двойной Жилы", "legendary", "tool", "vein", ["mine"],
       passives={"job_bonus": {"mine": 0.10}},
       charge={"code": "double_loot_mine", "cooldown_hours": 24},
       desc="Заряд: гарантированный доп. дроп с шахты"),
    _i("merciful_scales", "Весы Милосердия", "legendary", "tool", "trade", ["market"],
       passives={"job_bonus": {"market": 0.08}, "tax_add": -0.02},
       charge={"code": "no_tax_3", "cooldown_hours": 36},
       desc="Заряд: 3 работы без налога"),
    _i("warlord_horn", "Рог Полководец", "legendary", "relic", "raid", ["raid"],
       passives={"raid_mult": 0.08},
       charge={"code": "war_score_bonus", "cooldown_hours": 12},
       desc="Заряд: +2 очка войны бесед с рейда"),
)


def get_item(item_id: str) -> dict | None:
    return ITEMS.get(item_id)


def all_items() -> list[dict]:
    return list(ITEMS.values())


def catalog_size() -> int:
    return len(ITEMS)


def items_in_pool(pool: str, rarity: str | None = None) -> list[dict]:
    out = []
    for it in ITEMS.values():
        if pool not in it["pools"]:
            continue
        if rarity and it["rarity"] != rarity:
            continue
        out.append(it)
    return out


def format_item(it: dict) -> str:
    mark = RARITY_MARK.get(it["rarity"], "⬜")
    label = RARITY_LABEL.get(it["rarity"], it["rarity"])
    return f"{mark} [{label}] {it['name']}"


def format_buffs(it: dict) -> str:
    """Человекочитаемые баффы / заряд / аура для карточки и торга."""
    lines: list[str] = []
    if it.get("desc"):
        lines.append(it["desc"])
    p = it.get("passives") or {}
    job_names = {
        "mine": "шахта",
        "market": "рынок",
        "guard": "охрана",
        "fish": "рыбалка",
        "farm": "поле",
        "forge": "кузня",
        "tavern": "таверна",
    }
    if p.get("work_mult"):
        lines.append(f"• Все работы: {p['work_mult']:+.0%}")
    for job, bonus in (p.get("job_bonus") or {}).items():
        lines.append(f"• {job_names.get(job, job)}: {bonus:+.0%}")
    if p.get("raid_mult"):
        lines.append(f"• Рейд: {p['raid_mult']:+.0%}")
    if p.get("raid_defend"):
        lines.append(f"• Защита казны: {p['raid_defend']:+.0%}")
    if p.get("raid_cd_hours"):
        lines.append(f"• КД рейда: {p['raid_cd_hours']:+.2f}ч")
    if p.get("raid_leader_share"):
        lines.append(f"• Доля лидера: {p['raid_leader_share']:+.0%}")
    if p.get("tax_add"):
        lines.append(f"• Налог с работ: {p['tax_add']:+.0%}")
    if p.get("smuggle_chance"):
        lines.append(f"• Шанс контрабанды: {p['smuggle_chance']:+.0%}")
    if p.get("smuggle_reward"):
        lines.append(f"• Награда контрабанды: {p['smuggle_reward']:+.0%}")
    if p.get("smuggle_fine_mult") and p["smuggle_fine_mult"] != 1:
        lines.append(f"• Штраф контрабанды ×{p['smuggle_fine_mult']}")
    if p.get("jail_hours_mult") and p["jail_hours_mult"] != 1:
        lines.append(f"• Тюрьма ×{p['jail_hours_mult']}")
    if p.get("treasury_bonus_add"):
        lines.append(f"• В казну с охраны: +{p['treasury_bonus_add']}")
    if p.get("loot_luck"):
        lines.append(f"• Удача лута: {p['loot_luck']:+.0%}")
    charge = it.get("charge")
    if charge:
        lines.append(
            f"⚡ Заряд `{charge['code']}` · КД {charge.get('cooldown_hours', '?')}ч"
        )
    aura = it.get("aura") or {}
    if aura.get("nation_work_mult"):
        lines.append(f"🌫 Аура страны (работы): {aura['nation_work_mult']:+.0%}")
    if aura.get("nation_treasury_raid_defend"):
        lines.append(
            f"🌫 Аура защиты казны: {aura['nation_treasury_raid_defend']:+.0%}"
        )
    if aura.get("personal_gold_vein"):
        lines.append("🌫 Для тебя всегда «золотая жила»")
    if aura.get("raid_target_mark"):
        lines.append("🌫 Страна помечена как богатая добыча")
    slot = SLOT_LABEL.get(it.get("slot", ""), it.get("slot", ""))
    if slot:
        lines.append(f"Слот: {slot}")
    # unique lines, keep order
    seen = set()
    out = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            out.append(line)
    return "\n".join(out) if out else "Без особых бонусов"


def search_catalog(query: str, *, rarity: str | None = None, limit: int = 20) -> list[dict]:
    q = (query or "").strip().casefold()
    out = []
    for it in ITEMS.values():
        if rarity and it["rarity"] != rarity:
            continue
        if q and q not in it["name"].casefold() and q not in it["id"].casefold():
            if q not in (it.get("desc") or "").casefold():
                continue
        out.append(it)
        if len(out) >= limit:
            break
    return out
