"""
generate_data.py
Generates two CSV files with fake Ukrainian people + tax IDs (ІПН).

  big_list.csv   — 1000 records  → import into Google Sheets
  small_list.csv —   50 records  → import into Numbers (Mac) / Excel (Win)
                    ~25 of the 50 overlap with big_list (the rest are unique)

Usage:
    python generate_data.py
"""

import csv
import random

# ── Name pools ────────────────────────────────────────────────────────────────

SURNAMES = [
    "Коваленко", "Бондаренко", "Мельник", "Кравченко", "Олійник",
    "Шевченко", "Ткаченко", "Кириленко", "Савченко", "Гриценко",
    "Марченко", "Лисенко", "Павленко", "Семенченко", "Яценко",
    "Романенко", "Захаренко", "Луценко", "Тимченко", "Поліщук",
    "Руденко", "Костенко", "Данченко", "Іваненко", "Петренко",
    "Сидоренко", "Карпенко", "Гончаренко", "Зінченко", "Дяченко",
    "Пономаренко", "Харченко", "Власенко", "Момот", "Білоус",
    "Дмитренко", "Середа", "Литвиненко", "Клименко", "Деркач",
    "Кузьменко", "Нечипоренко", "Степаненко", "Григоренко", "Орленко",
    "Мороз", "Войтенко", "Передерій", "Назаренко", "Бойченко",
    "Горобець", "Панченко", "Ткач", "Левченко", "Хоменко",
    "Сорока", "Білик", "Гладченко", "Нагірняк", "Кисіль",
]

MALE_NAMES = [
    "Олексій", "Іван", "Петро", "Микола", "Василь",
    "Андрій", "Сергій", "Михайло", "Олег", "Юрій",
    "Дмитро", "Богдан", "Тарас", "Владислав", "Роман",
    "Максим", "Євген", "Вадим", "Артем", "Ігор",
    "Віктор", "Анатолій", "Валерій", "Геннадій", "Ярослав",
]

FEMALE_NAMES = [
    "Оксана", "Наталія", "Ірина", "Тетяна", "Олена",
    "Людмила", "Ганна", "Марія", "Вікторія", "Юлія",
    "Ольга", "Лариса", "Валентина", "Надія", "Світлана",
    "Катерина", "Діана", "Аліна", "Дарина", "Поліна",
    "Зоя", "Галина", "Антоніна", "Тамара", "Лілія",
]

MALE_PATRONYMICS = [
    "Олексійович", "Іванович", "Петрович", "Миколайович", "Васильович",
    "Андрійович", "Сергійович", "Михайлович", "Олегович", "Юрійович",
    "Дмитрович", "Богданович", "Тарасович", "Романович", "Максимович",
    "Євгенович", "Вадимович", "Артемович", "Ігорович", "Владиславович",
]

FEMALE_PATRONYMICS = [
    "Олексіївна", "Іванівна", "Петрівна", "Миколаївна", "Василівна",
    "Андріївна", "Сергіївна", "Михайлівна", "Олегівна", "Юріївна",
    "Дмитрівна", "Богданівна", "Тарасівна", "Романівна", "Максимівна",
    "Євгенівна", "Вадимівна", "Артемівна", "Ігорівна", "Владиславівна",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _unique_ipn(existing: set) -> str:
    """Generate a unique 10-digit Ukrainian-style IPN."""
    while True:
        ipn = str(random.randint(1000000000, 9999999999))
        if ipn not in existing:
            existing.add(ipn)
            return ipn


def _person(existing_ipns: set) -> tuple:
    gender = random.choice(("M", "F"))
    surname = random.choice(SURNAMES)
    if gender == "M":
        name = random.choice(MALE_NAMES)
        patronymic = random.choice(MALE_PATRONYMICS)
    else:
        name = random.choice(FEMALE_NAMES)
        patronymic = random.choice(FEMALE_PATRONYMICS)
    return f"{surname} {name} {patronymic}", _unique_ipn(existing_ipns)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    existing_ipns: set = set()

    # 1 000 people for Google Sheets
    big_list = [_person(existing_ipns) for _ in range(1000)]

    # ~25 entries taken from big_list …
    overlap_indices = random.sample(range(len(big_list)), 25)
    small_list = [big_list[i] for i in overlap_indices]

    # … plus 25 brand-new entries NOT in big_list
    while len(small_list) < 50:
        small_list.append(_person(existing_ipns))

    random.shuffle(small_list)

    # Write big_list.csv  (utf-8-sig = BOM for Excel/Numbers auto-detection)
    with open("big_list.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["ПІБ", "ІПН", "Знайдено"])
        for pib, ipn in big_list:
            w.writerow([pib, ipn, ""])

    # Write small_list.csv
    with open("small_list.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["ПІБ", "ІПН"])
        for pib, ipn in small_list:
            w.writerow([pib, ipn])

    big_ipns = {ipn for _, ipn in big_list}
    overlap_count = sum(1 for _, ipn in small_list if ipn in big_ipns)

    print(f"✓  big_list.csv   — 1 000 записів")
    print(f"✓  small_list.csv —    50 записів  ({overlap_count} збігів з big_list)")
    print()
    print("Наступні кроки:")
    print("  Google Sheets  : Файл → Імпорт → big_list.csv")
    print("                   Потім виділи колонку C → Insert → Checkbox")
    print("  Numbers / Excel: імпортуй small_list.csv (дані з рядка 2)")


if __name__ == "__main__":
    main()
