from __future__ import annotations

import re


CYRILLIC_TO_LATIN = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "yo",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


TRANSLATION_REPLACEMENTS: list[tuple[str, str]] = [
    ("Закрытые корейские бургеры", "Closed Korean Burgers"),
    ("Студенческое меню", "Student Menu"),
    ("Весеннее меню", "Spring Menu"),
    ("Основное меню", "Main Menu"),
    ("Авторские напитки", "Signature Drinks"),
    ("Большая пицца", "Large Pizza"),
    ("Закрытая пицца", "Closed Pizza"),
    ("Вторые блюда", "Main Courses"),
    ("Бабл чай", "Bubble Tea"),
    ("Фаст-фуд", "Fast Food"),
    ("молочная пена", "milk foam"),
    ("горячая вода", "hot water"),
    ("взбитые сливки", "whipped cream"),
    ("красный лук", "red onion"),
    ("зеленый лук", "green onion"),
    ("болгарский перец", "bell pepper"),
    ("маринованные огурцы", "pickles"),
    ("томатный соус", "tomato sauce"),
    ("белый соус", "white sauce"),
    ("сырный соус", "cheese sauce"),
    ("чесночный соус", "garlic sauce"),
    ("соус ранч", "ranch sauce"),
    ("соус цезарь", "Caesar sauce"),
    ("соус аджика", "adjika sauce"),
    ("соус терияки", "teriyaki sauce"),
    ("соус тейсти", "Tasty sauce"),
    ("сыр моцарелла", "mozzarella cheese"),
    ("сыр чеддер", "cheddar cheese"),
    ("сыр фета", "feta cheese"),
    ("томатный", "tomato"),
    ("классический", "classic"),
    ("черный кофе", "black coffee"),
    ("в фильтр-кофеварке", "in a filter coffee machine"),
    ("рисовая лапша", "rice noodles"),
    ("гречневая лапша", "buckwheat noodles"),
    ("пшеничная лапша", "wheat noodles"),
    ("сладкий перец", "sweet pepper"),
    ("сладкий чили", "sweet chili"),
    ("яблочный сок", "apple juice"),
    ("апельсиновый сок", "orange juice"),
    ("лимонный сок", "lemon juice"),
    ("кокосовое молоко", "coconut milk"),
    ("банановое молоко", "banana milk"),
    ("овсяное молоко", "oat milk"),
    ("фильтр-кофе", "filter coffee"),
    ("кофе", "coffee"),
    ("эспрессо", "espresso"),
    ("американо", "americano"),
    ("капучино", "cappuccino"),
    ("латте", "latte"),
    ("раф", "raf"),
    ("флэт уайт", "flat white"),
    ("бамбл", "bumble"),
    ("татарский", "Tatar"),
    ("малиновый", "raspberry"),
    ("смородиновый", "currant"),
    ("имбирный", "ginger"),
    ("облепиховый", "sea buckthorn"),
    ("цитрусовый", "citrus"),
    ("абрикосовый", "apricot"),
    ("каркаде", "hibiscus"),
    ("гранатовый", "pomegranate"),
    ("фундучное", "hazelnut"),
    ("фундучный", "hazelnut"),
    ("какао", "cocoa"),
    ("айс", "iced"),
    ("вишневый", "cherry"),
    ("вишнёвый", "cherry"),
    ("клубника", "strawberry"),
    ("банан", "banana"),
    ("арбуз", "watermelon"),
    ("гуава", "guava"),
    ("личи", "lychee"),
    ("мороженое", "ice cream"),
    ("печенье", "cookie"),
    ("творожные", "cottage cheese"),
    ("блинчики", "pancakes"),
    ("ролл", "roll"),
    ("омлет", "omelet"),
    ("овсяная", "oat"),
    ("каша", "porridge"),
    ("суп-лапша", "noodle soup"),
    ("суп", "soup"),
    ("салат", "salad"),
    ("цезарь", "Caesar"),
    ("стрипс", "strips"),
    ("паста", "pasta"),
    ("карбоне", "carbonara"),
    ("вок", "wok"),
    ("пад тай", "pad thai"),
    ("сэндвич", "sandwich"),
    ("чикенчиз", "chicken cheese"),
    ("чизбургер", "cheeseburger"),
    ("шаверма", "shawarma"),
    ("классик", "classic"),
    ("бургер", "burger"),
    ("тейсти", "Tasty"),
    ("пицца", "pizza"),
    ("маргарита", "Margherita"),
    ("мясная", "Meat"),
    ("дачная", "Country"),
    ("сборная", "Combo"),
    ("кола", "cola"),
    ("лимонад", "lemonade"),
    ("горячий шоколад", "hot chocolate"),
    ("лимонный пирог", "lemon pie"),
    ("ромашка", "chamomile"),
    ("черника", "blueberry"),
    ("юдзу", "yuzu"),
    ("грибной", "mushroom"),
    ("баклажан", "eggplant"),
    ("манго", "mango"),
    ("рамен", "ramen"),
    ("нут", "chickpea"),
    ("гречески", "Greek-style"),
    ("пибимпап", "bibimbap"),
    ("пирожное", "cake"),
    ("карамельное", "caramel"),
    ("гречка", "buckwheat"),
    ("слойка", "pastry"),
    ("груша", "pear"),
    ("чай", "tea"),
    ("десерты", "Desserts"),
    ("завтраки", "Breakfast"),
    ("супы", "Soups"),
    ("салаты", "Salads"),
    ("пицца", "Pizza"),
    ("хот-доги", "Hot Dogs"),
    ("чай", "Tea"),
    ("кофе", "Coffee"),
    ("молоко", "milk"),
    ("сливки", "cream"),
    ("горячий", "hot"),
    ("черный", "black"),
    ("заваренный", "brewed"),
    ("насыщенный", "rich"),
    ("кофейный", "coffee"),
    ("вкус", "flavor"),
    ("текстурное", "textured"),
    ("ванильный", "vanilla"),
    ("сахар", "sugar"),
    ("сок", "juice"),
    ("лед", "ice"),
    ("листья", "leaves"),
    ("смородины", "currant"),
    ("мелисса", "lemon balm"),
    ("чабрец", "thyme"),
    ("душица", "oregano"),
    ("малина", "raspberry"),
    ("лимон", "lemon"),
    ("мята", "mint"),
    ("розмарин", "rosemary"),
    ("мед", "honey"),
    ("лайм", "lime"),
    ("корица", "cinnamon"),
    ("улун", "oolong"),
    ("джем", "jam"),
    ("сироп", "syrup"),
    ("бузины", "elderflower"),
    ("анис", "anise"),
    ("топпинг", "topping"),
    ("куркума", "turmeric"),
    ("курица", "chicken"),
    ("говядина", "beef"),
    ("говяжий", "beef"),
    ("грудка", "breast"),
    ("филе", "fillet"),
    ("ветчина", "ham"),
    ("бекон", "bacon"),
    ("шампиньоны", "champignons"),
    ("грибы", "mushrooms"),
    ("моцарелла", "mozzarella"),
    ("рикотта", "ricotta"),
    ("чеддер", "cheddar"),
    ("пармезан", "Parmesan"),
    ("дор блю", "dor blue"),
    ("авокадо", "avocado"),
    ("огурцы", "cucumbers"),
    ("томаты", "tomatoes"),
    ("чеснок", "garlic"),
    ("кинза", "cilantro"),
    ("картофельные дольки", "potato wedges"),
    ("рис", "rice"),
    ("чиабатта", "ciabatta"),
    ("тортилья", "tortilla"),
    ("булочка", "bun"),
    ("бриошь", "brioche"),
    ("наггетсы", "nuggets"),
    ("картофель фри", "French fries"),
    ("и", "and"),
]

MODERNIZED_SOURCES = {
    "классический",
    "черный кофе",
    "в фильтр-кофеварке",
    "айс",
    "горячий",
    "черный",
    "заваренный",
    "насыщенный",
    "кофейный",
    "вкус",
    "текстурное",
    "и",
}


UNIT_REPLACEMENTS = {
    " мл": " ml",
    " гр": " g",
    " см": " cm",
    " шт": " pcs",
}


SMART_PHRASE_REPLACEMENTS: list[tuple[str, str]] = [
    ("Грибной сэндвич с баклажанами", "Mushroom Sandwich with Eggplant"),
    ("Мексиканская торта", "Mexican Torta"),
    ("Фермерский завтрак", "Farmer's Breakfast"),
    ("Французский омлет", "French Omelet"),
    ("Курица по-дижонски", "Dijon Chicken"),
    ("Вок с курицей", "Wok with Chicken"),
    ("Сэндвич с курицей", "Sandwich with Chicken"),
    ("Мясной сэндвич", "Meat Sandwich"),
    ("Ананас-терияки бургер", "Pineapple Teriyaki Burger"),
    ("Классический хот-дог", "Classic Hot Dog"),
    ("Французский хот-дог", "French Hot Dog"),
    ("Пицца чикен пармеджано", "Chicken Parmigiano Pizza"),
    ("Пицца «Бургерная»", "Burger Pizza"),
    ("Закрытая пицца по-абхазски", "Closed Abkhaz-Style Pizza"),
    ("Закрытый бургер Тейсти", "Closed Tasty Burger"),
    ("Закрытый Цезарь бургер", "Closed Caesar Burger"),
    ("Вишнёвый пирожок", "Cherry Pie"),
    ("Барбарисовый лимонад", "Barberry Lemonade"),
    ("Горячий шоколад с мятой", "Hot Chocolate with Mint"),
    ("Юдзу шприц", "Yuzu Spritz"),
    ("Сезонная позиция", "Seasonal item"),
    ("Куриный суп-лапша", "Chicken Noodle Soup"),
    ("говяжий фарш", "ground beef"),
    ("куриный бульон", "chicken broth"),
    ("говяжий бульон", "beef broth"),
    ("Фо бо", "Pho Bo"),
    ("Фо га", "Pho Ga"),
    ("фо бо", "Pho Bo"),
    ("фо га", "Pho Ga"),
    ("крем-суп", "cream soup"),
    ("хашбраун", "hash brown"),
    ("чизкейк", "cheesecake"),
    ("с начинкой на выбор", "with filling of your choice"),
    ("с соусом на выбор", "with sauce of your choice"),
    ("на выбор", "of your choice"),
    ("на молоке", "with milk"),
    ("из двух яиц", "with two eggs"),
    ("домашняя лапша", "homemade noodles"),
    ("джус боллы", "juice balls"),
    ("шоколад молочный", "milk chocolate"),
    ("сдобное дрожжевое тесто", "sweet yeast dough"),
    ("грецким орехом", "walnut"),
    ("в панировке", "breaded"),
    ("томаты черри", "cherry tomatoes"),
    ("соевый соус", "soy sauce"),
    ("охотничьи колбаски", "hunter's sausages"),
    ("свежими овощами", "fresh vegetables"),
    ("белый шоколадный сироп", "white chocolate syrup"),
    ("перец болгарский", "bell pepper"),
    ("красная жареная капуста", "fried red cabbage"),
    ("корейская морковь", "Korean carrot"),
    ("домашняя", "homemade"),
    ("домашний", "homemade"),
    ("савоярди", "savoiardi"),
]


SMART_TOKEN_TRANSLATIONS = {
    "с": "with",
    "со": "with",
    "и": "and",
    "или": "or",
    "в": "in",
    "во": "in",
    "на": "with",
    "из": "from",
    "для": "for",
    "без": "without",
    "по": "style",
    "гр": "g",
    "мл": "ml",
    "см": "cm",
    "шт": "pcs",
}


SMART_STEM_TRANSLATIONS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"баклажан[а-яё-]*", re.IGNORECASE), "eggplant"),
    (re.compile(r"шампиньон[а-яё-]*", re.IGNORECASE), "champignons"),
    (re.compile(r"грибн[а-яё-]*", re.IGNORECASE), "mushroom"),
    (re.compile(r"гриб[а-яё-]*", re.IGNORECASE), "mushrooms"),
    (re.compile(r"соус[а-яё-]*", re.IGNORECASE), "sauce"),
    (re.compile(r"сливк[а-яё-]*", re.IGNORECASE), "cream"),
    (re.compile(r"сливочн[а-яё-]*", re.IGNORECASE), "creamy"),
    (re.compile(r"молок[а-яё-]*", re.IGNORECASE), "milk"),
    (re.compile(r"молочн[а-яё-]*", re.IGNORECASE), "milk"),
    (re.compile(r"яблок[а-яё-]*", re.IGNORECASE), "apple"),
    (re.compile(r"яблочн[а-яё-]*", re.IGNORECASE), "apple"),
    (re.compile(r"изюм[а-яё-]*", re.IGNORECASE), "raisins"),
    (re.compile(r"варень[а-яё-]*", re.IGNORECASE), "jam"),
    (re.compile(r"сгущенк[а-яё-]*", re.IGNORECASE), "condensed milk"),
    (re.compile(r"варен[а-яё-]*", re.IGNORECASE), "boiled"),
    (re.compile(r"говяж[а-яё-]*", re.IGNORECASE), "beef"),
    (re.compile(r"говядин[а-яё-]*", re.IGNORECASE), "beef"),
    (re.compile(r"курин[а-яё-]*", re.IGNORECASE), "chicken"),
    (re.compile(r"курино[а-яё-]*", re.IGNORECASE), "chicken"),
    (re.compile(r"куриц[а-яё-]*", re.IGNORECASE), "chicken"),
    (re.compile(r"цыпленк[а-яё-]*", re.IGNORECASE), "chicken"),
    (re.compile(r"фарш[а-яё-]*", re.IGNORECASE), "mince"),
    (re.compile(r"колбаск[а-яё-]*", re.IGNORECASE), "sausage"),
    (re.compile(r"томат[а-яё-]*", re.IGNORECASE), "tomatoes"),
    (re.compile(r"помидор[а-яё-]*", re.IGNORECASE), "tomatoes"),
    (re.compile(r"огурц[а-яё-]*", re.IGNORECASE), "cucumbers"),
    (re.compile(r"айсберг", re.IGNORECASE), "iceberg lettuce"),
    (re.compile(r"перц[а-яё-]*", re.IGNORECASE), "pepper"),
    (re.compile(r"лук[а-яё-]*", re.IGNORECASE), "onion"),
    (re.compile(r"сыр[а-яё-]*", re.IGNORECASE), "cheese"),
    (re.compile(r"сырн[а-яё-]*", re.IGNORECASE), "cheese"),
    (re.compile(r"ветчин[а-яё-]*", re.IGNORECASE), "ham"),
    (re.compile(r"бекон[а-яё-]*", re.IGNORECASE), "bacon"),
    (re.compile(r"яйц[а-яё-]*", re.IGNORECASE), "egg"),
    (re.compile(r"глазунь[а-яё-]*", re.IGNORECASE), "fried egg"),
    (re.compile(r"лапш[а-яё-]*", re.IGNORECASE), "noodles"),
    (re.compile(r"бульон[а-яё-]*", re.IGNORECASE), "broth"),
    (re.compile(r"зелень", re.IGNORECASE), "greens"),
    (re.compile(r"гренк[а-яё-]*", re.IGNORECASE), "croutons"),
    (re.compile(r"чесночн[а-яё-]*", re.IGNORECASE), "garlic"),
    (re.compile(r"горчиц[а-яё-]*", re.IGNORECASE), "mustard"),
    (re.compile(r"кунжут[а-яё-]*", re.IGNORECASE), "sesame"),
    (re.compile(r"соев[а-яё-]*", re.IGNORECASE), "soy"),
    (re.compile(r"чиабатт[а-яё-]*", re.IGNORECASE), "ciabatta"),
    (re.compile(r"бриош[а-яё-]*", re.IGNORECASE), "brioche"),
    (re.compile(r"булочк[а-яё-]*", re.IGNORECASE), "bun"),
    (re.compile(r"тортиль[а-яё-]*", re.IGNORECASE), "tortilla"),
    (re.compile(r"рисов[а-яё-]*", re.IGNORECASE), "rice"),
    (re.compile(r"рис[а-яё-]*", re.IGNORECASE), "rice"),
    (re.compile(r"гречнев[а-яё-]*", re.IGNORECASE), "buckwheat"),
    (re.compile(r"пшеничн[а-яё-]*", re.IGNORECASE), "wheat"),
    (re.compile(r"салат[а-яё-]*", re.IGNORECASE), "salad"),
    (re.compile(r"суп[а-яё-]*", re.IGNORECASE), "soup"),
    (re.compile(r"каш[а-яё-]*", re.IGNORECASE), "porridge"),
    (re.compile(r"омлет[а-яё-]*", re.IGNORECASE), "omelet"),
    (re.compile(r"ролл[а-яё-]*", re.IGNORECASE), "roll"),
    (re.compile(r"блинчик[а-яё-]*", re.IGNORECASE), "pancakes"),
    (re.compile(r"творожн[а-яё-]*", re.IGNORECASE), "cottage cheese"),
    (re.compile(r"орех[а-яё-]*", re.IGNORECASE), "nuts"),
    (re.compile(r"грецк[а-яё-]*", re.IGNORECASE), "walnut"),
    (re.compile(r"морковн[а-яё-]*", re.IGNORECASE), "carrot"),
    (re.compile(r"корейск[а-яё-]*", re.IGNORECASE), "Korean"),
    (re.compile(r"шоколадн[а-яё-]*", re.IGNORECASE), "chocolate"),
    (re.compile(r"маков[а-яё-]*", re.IGNORECASE), "poppy"),
    (re.compile(r"крем[а-яё-]*", re.IGNORECASE), "cream"),
    (re.compile(r"свежевыжат[а-яё-]*", re.IGNORECASE), "freshly squeezed"),
    (re.compile(r"апельсинов[а-яё-]*", re.IGNORECASE), "orange"),
    (re.compile(r"лимонн[а-яё-]*", re.IGNORECASE), "lemon"),
    (re.compile(r"клубничн[а-яё-]*", re.IGNORECASE), "strawberry"),
    (re.compile(r"карамельн[а-яё-]*", re.IGNORECASE), "caramel"),
    (re.compile(r"копчен[а-яё-]*", re.IGNORECASE), "smoked"),
    (re.compile(r"классическ[а-яё-]*", re.IGNORECASE), "classic"),
    (re.compile(r"свеж[а-яё-]*", re.IGNORECASE), "fresh"),
    (re.compile(r"бел[а-яё-]*", re.IGNORECASE), "white"),
    (re.compile(r"мексиканск[а-яё-]*", re.IGNORECASE), "Mexican"),
    (re.compile(r"фермерск[а-яё-]*", re.IGNORECASE), "farmer's"),
    (re.compile(r"французск[а-яё-]*", re.IGNORECASE), "French"),
    (re.compile(r"мясн[а-яё-]*", re.IGNORECASE), "meat"),
    (re.compile(r"ананас[а-яё-]*", re.IGNORECASE), "pineapple"),
    (re.compile(r"закрыт[а-яё-]*", re.IGNORECASE), "closed"),
    (re.compile(r"облепих[а-яё-]*", re.IGNORECASE), "sea buckthorn"),
    (re.compile(r"барбарисов[а-яё-]*", re.IGNORECASE), "barberry"),
    (re.compile(r"тростников[а-яё-]*", re.IGNORECASE), "cane"),
    (re.compile(r"содов[а-яё-]*", re.IGNORECASE), "soda water"),
    (re.compile(r"арбузн[а-яё-]*", re.IGNORECASE), "watermelon"),
    (re.compile(r"гуав[а-яё-]*", re.IGNORECASE), "guava"),
    (re.compile(r"пюр[а-яё-]*", re.IGNORECASE), "puree"),
    (re.compile(r"джус[а-яё-]*", re.IGNORECASE), "juice"),
    (re.compile(r"болл[а-яё-]*", re.IGNORECASE), "balls"),
    (re.compile(r"ромашк[а-яё-]*", re.IGNORECASE), "chamomile"),
    (re.compile(r"лаванд[а-яё-]*", re.IGNORECASE), "lavender"),
    (re.compile(r"мят[а-яё-]*", re.IGNORECASE), "mint"),
    (re.compile(r"безалкогольн[а-яё-]*", re.IGNORECASE), "non-alcoholic"),
    (re.compile(r"шампанск[а-яё-]*", re.IGNORECASE), "sparkling wine"),
    (re.compile(r"кокосов[а-яё-]*", re.IGNORECASE), "coconut"),
    (re.compile(r"лепестк[а-яё-]*", re.IGNORECASE), "flakes"),
    (re.compile(r"миндал[а-яё-]*", re.IGNORECASE), "almond"),
    (re.compile(r"медово-оливков[а-яё-]*", re.IGNORECASE), "honey-olive"),
    (re.compile(r"семг[а-яё-]*", re.IGNORECASE), "salmon"),
    (re.compile(r"жарен[а-яё-]*", re.IGNORECASE), "fried"),
    (re.compile(r"капуст[а-яё-]*", re.IGNORECASE), "cabbage"),
    (re.compile(r"котлет[а-яё-]*", re.IGNORECASE), "patty"),
    (re.compile(r"морков[а-яё-]*", re.IGNORECASE), "carrot"),
    (re.compile(r"черри", re.IGNORECASE), "cherry"),
    (re.compile(r"панировк[а-яё-]*", re.IGNORECASE), "breading"),
    (re.compile(r"охотнич[а-яё-]*", re.IGNORECASE), "hunter's"),
    (re.compile(r"бисквит[а-яё-]*", re.IGNORECASE), "sponge cake"),
    (re.compile(r"корж[а-яё-]*", re.IGNORECASE), "cake layers"),
    (re.compile(r"сло[яе][а-яё-]*", re.IGNORECASE), "layers"),
    (re.compile(r"тест[а-яё-]*", re.IGNORECASE), "dough"),
    (re.compile(r"дрожжев[а-яё-]*", re.IGNORECASE), "yeast"),
    (re.compile(r"начинк[а-яё-]*", re.IGNORECASE), "filling"),
    (re.compile(r"стружк[а-яё-]*", re.IGNORECASE), "shavings"),
    (re.compile(r"чикен", re.IGNORECASE), "chicken"),
    (re.compile(r"пармеджано", re.IGNORECASE), "parmigiano"),
    (re.compile(r"пирожок", re.IGNORECASE), "pie"),
    (re.compile(r"шприц", re.IGNORECASE), "spritz"),
    (re.compile(r"сезонн[а-яё-]*", re.IGNORECASE), "seasonal"),
    (re.compile(r"позиц[а-яё-]*", re.IGNORECASE), "item"),
    (re.compile(r"завтрак[а-яё-]*", re.IGNORECASE), "breakfast"),
    (re.compile(r"десерт[а-яё-]*", re.IGNORECASE), "dessert"),
    (re.compile(r"овощ[а-яё-]*", re.IGNORECASE), "vegetables"),
]


CYRILLIC_TOKEN_PATTERN = re.compile(r"[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)*")
ALPHABETIC_TOKEN_PATTERN = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)?")
TRANSLATION_TOKEN_PATTERN = re.compile(
    r"[A-Za-z]+(?:[-'][A-Za-z]+)?|[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)*|\d+(?:[.,:/-]\d+)*|\s+|[^\w\s]",
)
TITLECASE_SMALL_WORDS = {"a", "an", "and", "for", "from", "in", "of", "on", "or", "the", "to", "with"}


def _match_case(replacement: str, source: str) -> str:
    if not source:
        return replacement
    if source.isupper():
        return replacement.upper()
    if source[0].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def _apply_case_insensitive_replacements(
    text: str,
    *,
    include_modernized: bool = True,
) -> str:
    translated = text
    for source, target in sorted(
        TRANSLATION_REPLACEMENTS,
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        if not include_modernized and source in MODERNIZED_SOURCES:
            continue
        pattern = re.compile(rf"(?<!\w){re.escape(source)}(?!\w)", re.IGNORECASE)
        translated = pattern.sub(
            lambda match: _match_case(target, match.group(0)),
            translated,
        )
    return translated


def transliterate_text(text: str) -> str:
    result: list[str] = []
    for character in text:
        lower_character = character.lower()
        if lower_character not in CYRILLIC_TO_LATIN:
            result.append(character)
            continue

        replacement = CYRILLIC_TO_LATIN[lower_character]
        if character.isupper() and replacement:
            replacement = replacement[:1].upper() + replacement[1:]
        result.append(replacement)

    return "".join(result)


def _translate_menu_text_v1(text: str, *, include_modernized: bool) -> str:
    if not text.strip():
        return ""

    translated = _apply_case_insensitive_replacements(
        text,
        include_modernized=include_modernized,
    )
    for source, target in UNIT_REPLACEMENTS.items():
        translated = translated.replace(source, target)
    translated = transliterate_text(translated)
    translated = re.sub(r"\s+", " ", translated).strip()
    return translated


def _apply_smart_phrase_replacements(text: str) -> str:
    translated = text
    replacements = SMART_PHRASE_REPLACEMENTS + TRANSLATION_REPLACEMENTS
    for source, target in sorted(replacements, key=lambda item: len(item[0]), reverse=True):
        pattern = re.compile(rf"(?<!\w){re.escape(source)}(?!\w)", re.IGNORECASE)
        translated = pattern.sub(
            lambda match: _match_case(target, match.group(0)),
            translated,
        )
    return translated


def _translate_smart_token(token: str) -> str:
    lowered = token.lower()
    if lowered in SMART_TOKEN_TRANSLATIONS:
        return _match_case(SMART_TOKEN_TRANSLATIONS[lowered], token)

    for pattern, target in SMART_STEM_TRANSLATIONS:
        if pattern.fullmatch(token):
            return _match_case(target, token)

    return transliterate_text(token)


def _normalize_translated_spacing(text: str) -> str:
    normalized = re.sub(r"\s*/\s*", " / ", text)
    normalized = re.sub(r"\s+([,.;:!?])", r"\1", normalized)
    normalized = re.sub(r"([(\[]) +", r"\1", normalized)
    normalized = re.sub(r" +([)\]])", r"\1", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _sentence_case_text(text: str) -> str:
    if not text:
        return text

    for index, character in enumerate(text):
        if character.isalpha():
            return text[:index] + character.upper() + text[index + 1 :]
    return text


def _titleize_text(text: str) -> str:
    result: list[str] = []
    last_index = 0
    first_word = True

    for match in ALPHABETIC_TOKEN_PATTERN.finditer(text):
        result.append(text[last_index : match.start()])
        word = match.group(0)
        lowered = word.lower()
        if word.isupper() and len(word) <= 4:
            result.append(word)
        elif not first_word and lowered in TITLECASE_SMALL_WORDS:
            result.append(lowered)
        else:
            result.append(lowered[:1].upper() + lowered[1:])
        first_word = False
        last_index = match.end()

    result.append(text[last_index:])
    return "".join(result)


def _translate_menu_text_v2(text: str) -> str:
    if not text.strip():
        return ""

    translated = _apply_smart_phrase_replacements(text)
    for source, target in UNIT_REPLACEMENTS.items():
        translated = translated.replace(source, target)

    translated_parts: list[str] = []
    for token in TRANSLATION_TOKEN_PATTERN.findall(translated):
        if not CYRILLIC_TOKEN_PATTERN.search(token):
            translated_parts.append(token)
            continue
        translated_parts.append(_translate_smart_token(token))

    return _normalize_translated_spacing("".join(translated_parts))


def translate_menu_text(text: str, *, context: str = "generic") -> str:
    translated = _translate_menu_text_v2(text)
    if context == "name":
        return _titleize_text(translated)
    if context in {"description", "ingredients"}:
        return _sentence_case_text(translated)
    return translated


def translate_menu_text_legacy(text: str) -> str:
    return _translate_menu_text_v1(text, include_modernized=False)


def translate_menu_text_previous(text: str) -> str:
    return _translate_menu_text_v1(text, include_modernized=True)


def ensure_secondary_language_fields(data: dict[str, object]) -> dict[str, object]:
    normalized = dict(data)
    normalized["name_en"] = str(normalized.get("name_en", "")).strip() or translate_menu_text(
        str(normalized.get("name", "")),
        context="name",
    )
    normalized["description_en"] = str(
        normalized.get("description_en", "")
    ).strip() or translate_menu_text(
        str(normalized.get("description", "")),
        context="description",
    )
    normalized["ingredients_en"] = str(
        normalized.get("ingredients_en", "")
    ).strip() or translate_menu_text(
        str(normalized.get("ingredients", "")),
        context="ingredients",
    )
    return normalized
