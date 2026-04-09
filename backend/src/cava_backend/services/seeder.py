from __future__ import annotations

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from cava_backend.database import engine
from cava_backend.models.menu_item import MenuCollectionRecord, MenuEntryRecord
from cava_backend.services.menu_localization import (
    ensure_secondary_language_fields,
    translate_menu_text,
    translate_menu_text_legacy,
    translate_menu_text_previous,
)
from cava_backend.services.menu_render_cache import invalidate_menu_render_cache


def variant(portion: str, price: float, label: str = "") -> dict[str, str | float]:
    return {"portion": portion, "price": price, "label": label}


def entry(
    *,
    name: str,
    menu_group: str,
    section: str,
    variants: list[dict[str, str | float]],
    ingredients: str = "",
    ingredients_en: str = "",
    description: str = "",
    description_en: str = "",
    name_en: str = "",
    tags: list[str] | None = None,
    image_url: str = "",
    is_featured: bool = False,
    position: int = 0,
) -> dict[str, object]:
    return ensure_secondary_language_fields(
        {
        "name": name,
        "name_en": name_en,
        "menu_group": menu_group,
        "section": section,
        "variants": variants,
        "ingredients": ingredients,
        "ingredients_en": ingredients_en,
        "description": description,
        "description_en": description_en,
        "tags": tags or [],
        "image_url": image_url,
        "is_available": True,
        "is_featured": is_featured,
        "position": position,
        }
    )


DEMO_MENU_ITEMS = [
    entry(
        name="Эспрессо",
        menu_group="Основное меню",
        section="Кофе",
        variants=[variant("40 мл", 160)],
        ingredients="Классический эспрессо.",
        position=1,
    ),
    entry(
        name="Американо",
        menu_group="Основное меню",
        section="Кофе",
        variants=[variant("200 мл", 180)],
        ingredients="Эспрессо и горячая вода.",
        position=2,
    ),
    entry(
        name="Капучино",
        menu_group="Основное меню",
        section="Кофе",
        variants=[variant("250 мл", 230), variant("350 мл", 250)],
        ingredients="Эспрессо, молоко, молочная пена.",
        is_featured=True,
        position=3,
    ),
    entry(
        name="Латте / Айс латте",
        menu_group="Основное меню",
        section="Кофе",
        variants=[variant("350 мл", 250)],
        ingredients="Эспрессо и молоко.",
        position=4,
    ),
    entry(
        name="Раф кофе",
        menu_group="Основное меню",
        section="Кофе",
        variants=[variant("250 мл", 260), variant("350 мл", 280)],
        ingredients="Эспрессо, сливки, ванильный сахар.",
        position=5,
    ),
    entry(
        name="Флэт уайт",
        menu_group="Основное меню",
        section="Кофе",
        variants=[variant("200 мл", 240)],
        ingredients="Насыщенный кофейный вкус и текстурное молоко.",
        position=6,
    ),
    entry(
        name="Фильтр-кофе",
        menu_group="Основное меню",
        section="Кофе",
        variants=[variant("200 мл", 210), variant("300 мл", 240)],
        ingredients="Черный кофе, заваренный в фильтр-кофеварке.",
        position=7,
    ),
    entry(
        name="Бамбл",
        menu_group="Основное меню",
        section="Кофе",
        variants=[variant("300 мл", 370)],
        ingredients="Эспрессо, апельсиновый сок, лед.",
        tags=["signature"],
        position=8,
    ),
    entry(
        name="Татарский чай",
        menu_group="Основное меню",
        section="Чай",
        variants=[variant("350 мл", 160)],
        ingredients="Листья смородины, мелисса, чабрец, душица.",
        position=1,
    ),
    entry(
        name="Малиновый чай",
        menu_group="Основное меню",
        section="Чай",
        variants=[variant("350 мл", 180)],
        ingredients="Малина, лимон, мята.",
        position=2,
    ),
    entry(
        name="Смородиновый чай",
        menu_group="Основное меню",
        section="Чай",
        variants=[variant("350 мл", 180)],
        ingredients="Смородина, черный чай, розмарин, лимон.",
        position=3,
    ),
    entry(
        name="Имбирный чай",
        menu_group="Основное меню",
        section="Чай",
        variants=[variant("350 мл", 160)],
        ingredients="Имбирь, лимон, мед, мята.",
        position=4,
    ),
    entry(
        name="Облепиховый чай",
        menu_group="Основное меню",
        section="Чай",
        variants=[variant("350 мл", 160)],
        ingredients="Облепиха, мед, мята.",
        position=5,
    ),
    entry(
        name="Цитрусовый чай",
        menu_group="Основное меню",
        section="Чай",
        variants=[variant("350 мл", 200)],
        ingredients="Лайм, тростниковый сахар, мята, корица.",
        position=6,
    ),
    entry(
        name="Абрикосовый чай",
        menu_group="Основное меню",
        section="Чай",
        variants=[variant("330 мл", 200)],
        ingredients="Улун, абрикосовый джем, яблочный сироп, лимон, мята.",
        position=7,
    ),
    entry(
        name="Чай каркаде-малина",
        menu_group="Основное меню",
        section="Чай",
        variants=[variant("300 мл", 200)],
        ingredients="Чай каркаде, малина, сироп бузины, мята.",
        tags=["new"],
        position=8,
    ),
    entry(
        name="Гранатовый американо",
        menu_group="Основное меню",
        section="Авторские напитки",
        variants=[variant("350 мл", 290)],
        ingredients="Гранатовый сок, эспрессо, сироп фалернум, анис.",
        position=1,
    ),
    entry(
        name="Облепиховый раф",
        menu_group="Основное меню",
        section="Авторские напитки",
        variants=[variant("250 мл", 300)],
        ingredients="Облепиховый эспрессо, облепиховый топпинг, куркума.",
        tags=["new"],
        position=2,
    ),
    entry(
        name="Топленое яблоко",
        menu_group="Основное меню",
        section="Авторские напитки",
        variants=[variant("500 мл", 280)],
        ingredients="Яблочный сок, карамельный сироп, яблочный сироп, овсяное молоко, корица, лед.",
        tags=["new"],
        position=3,
    ),
    entry(
        name="Фундучное какао",
        menu_group="Основное меню",
        section="Авторские напитки",
        variants=[variant("300 мл", 260)],
        ingredients="Фундучное молоко, какао, ванильный сахар.",
        position=4,
    ),
    entry(
        name="Орео милкшейк",
        menu_group="Основное меню",
        section="Авторские напитки",
        variants=[variant("300 мл", 300)],
        ingredients="Мороженое, молоко, печенье Oreo, взбитые сливки.",
        position=5,
    ),
    entry(
        name="Латте малиновый чизкейк",
        menu_group="Основное меню",
        section="Авторские напитки",
        variants=[variant("350 мл", 280)],
        ingredients="Молоко, эспрессо, малиновый топпинг, шоколадный сироп.",
        position=6,
    ),
    entry(
        name="Татарский раф",
        menu_group="Основное меню",
        section="Авторские напитки",
        variants=[variant("250 мл", 280), variant("350 мл", 320)],
        ingredients="Эспрессо, сливки, сироп на основе трав.",
        position=7,
    ),
    entry(
        name="Вишневый фильтр",
        menu_group="Основное меню",
        section="Авторские напитки",
        variants=[variant("300 мл", 280)],
        ingredients="Фильтр-кофе и вишневый соус.",
        position=8,
    ),
    entry(
        name="Клубника-банан",
        menu_group="Основное меню",
        section="Бабл чай",
        variants=[variant("350 мл", 350)],
        ingredients="Банановое молоко, клубничный топпинг, клубничные джус боллы, лед.",
        position=1,
    ),
    entry(
        name="Айс бабл латте",
        menu_group="Основное меню",
        section="Бабл чай",
        variants=[variant("450 мл", 390)],
        ingredients="Молоко, сливки, эспрессо, карамельные джус боллы, лед.",
        position=2,
    ),
    entry(
        name="Арбуз-гуава",
        menu_group="Основное меню",
        section="Бабл чай",
        variants=[variant("400 мл", 350)],
        ingredients="Содовая, арбузное пюре, сироп гуавы, клубничные джус боллы, лед.",
        position=3,
    ),
    entry(
        name="Бабл личи-гуава",
        menu_group="Основное меню",
        section="Бабл чай",
        variants=[variant("350 мл", 350)],
        ingredients="Содовая, сироп гуавы, джус боллы личи, лед.",
        tags=["new"],
        position=4,
    ),
    entry(
        name="Классический чизкейк",
        menu_group="Основное меню",
        section="Десерты",
        variants=[variant("100 гр", 230)],
        ingredients="Крем-чиз на песочной основе.",
        position=1,
    ),
    entry(
        name="Шоколадный торт",
        menu_group="Основное меню",
        section="Десерты",
        variants=[variant("120 гр", 300)],
        ingredients="Шоколадно-кофейные коржи с шоколадным кремом.",
        position=2,
    ),
    entry(
        name="Морковный торт",
        menu_group="Основное меню",
        section="Десерты",
        variants=[variant("110 гр", 230)],
        ingredients="Морковно-ореховый бисквит со слоями крем-чиза.",
        position=3,
    ),
    entry(
        name="Маковый торт",
        menu_group="Основное меню",
        section="Десерты",
        variants=[variant("120 гр", 230)],
        ingredients="Маковый бисквит с кремом из вареной сгущенки, изюмом и грецким орехом.",
        position=4,
    ),
    entry(
        name="Мексиканская торта",
        menu_group="Основное меню",
        section="Завтраки",
        variants=[variant("200 гр", 350)],
        ingredients="Чиабатта, колбаска чоризо, рикотта, авокадо, огурцы, красный лук, чеснок, кинза.",
        position=1,
    ),
    entry(
        name="Фермерский завтрак",
        menu_group="Основное меню",
        section="Завтраки",
        variants=[variant("300 гр", 420)],
        ingredients="Курино-говяжья колбаска, глазунья, картофельные дольки, соус сладкий чили.",
        position=2,
    ),
    entry(
        name="Сэндвич с ветчиной",
        menu_group="Основное меню",
        section="Завтраки",
        variants=[variant("220 гр", 220)],
        ingredients="Тосты, ветчина, омлет, огурцы, томаты.",
        position=3,
    ),
    entry(
        name="Творожные блинчики",
        menu_group="Основное меню",
        section="Завтраки",
        variants=[variant("200 гр", 220)],
        ingredients="Оладушки с творогом и соусом на выбор.",
        position=4,
    ),
    entry(
        name="Ролл с омлетом",
        menu_group="Основное меню",
        section="Завтраки",
        variants=[variant("220 гр", 220)],
        ingredients="Омлет с сыром пармезан и ветчиной в мексиканской тортилье.",
        position=5,
    ),
    entry(
        name="Овсяная каша",
        menu_group="Основное меню",
        section="Завтраки",
        variants=[variant("250 гр", 220)],
        ingredients="Каша на молоке с яблоком, изюмом или вареньем.",
        position=6,
    ),
    entry(
        name="Французский омлет",
        menu_group="Основное меню",
        section="Завтраки",
        variants=[variant("250 гр", 340)],
        ingredients="Омлет из двух яиц со сливками, сыром и начинкой на выбор.",
        position=7,
    ),
    entry(
        name="Хашбраун завтрак",
        menu_group="Основное меню",
        section="Завтраки",
        variants=[variant("210 гр", 340)],
        ingredients="Картофельные оладьи, яйцо, бекон, соус сальса.",
        position=8,
    ),
    entry(
        name="Апельсиновый фреш",
        menu_group="Основное меню",
        section="Завтраки",
        variants=[variant("250 мл", 370)],
        ingredients="Свежевыжатый апельсиновый сок.",
        position=9,
    ),
    entry(
        name="Сырный крем-суп",
        menu_group="Основное меню",
        section="Супы",
        variants=[variant("280 гр", 380)],
        ingredients="Сливочный суп с чесночными гренками.",
        position=1,
    ),
    entry(
        name="Грибной крем-суп",
        menu_group="Основное меню",
        section="Супы",
        variants=[variant("280 гр", 350)],
        ingredients="Сливочный суп с чесночными гренками.",
        position=2,
    ),
    entry(
        name="Куриный суп-лапша",
        menu_group="Основное меню",
        section="Супы",
        variants=[variant("370 гр", 210)],
        ingredients="Куриный бульон, домашняя лапша, курица, зелень.",
        position=3,
    ),
    entry(
        name="Фо бо / Фо га",
        menu_group="Основное меню",
        section="Супы",
        variants=[variant("650 гр", 550, "Фо бо"), variant("650 гр", 450, "Фо га")],
        ingredients="Говяжий или куриный бульон, рисовая лапша, лимон, красный лук, зелень.",
        tags=["new"],
        position=4,
    ),
    entry(
        name="Салат Цезарь",
        menu_group="Основное меню",
        section="Салаты",
        variants=[variant("250 гр", 480)],
        ingredients="Салат айсберг, филе курицы, гренки, соус цезарь, пармезан, томаты черри.",
        position=1,
    ),
    entry(
        name="Салат «Фреш Стрипс»",
        menu_group="Основное меню",
        section="Салаты",
        variants=[variant("250 гр", 350)],
        ingredients="Курица в панировке, салат айсберг, томаты черри, красный лук, ореховый соус, сладкий чили.",
        position=2,
    ),
    entry(
        name="Honey Chicken",
        menu_group="Основное меню",
        section="Вторые блюда",
        variants=[variant("260 гр", 420)],
        ingredients="Филе цыпленка, соевый соус, мед, чеснок, кунжут, зеленый лук.",
        position=1,
    ),
    entry(
        name="Курица по-дижонски",
        menu_group="Основное меню",
        section="Вторые блюда",
        variants=[variant("320 гр", 460)],
        ingredients="Курица под соусом с сыром и горчицей, гарнир из риса с луком и шампиньонами.",
        position=2,
    ),
    entry(
        name="Паста карбоне",
        menu_group="Основное меню",
        section="Вторые блюда",
        variants=[variant("350 гр", 510)],
        ingredients="Феттучини, ветчина, копченая грудка, сливочный соус.",
        position=3,
    ),
    entry(
        name="Вок с курицей",
        menu_group="Основное меню",
        section="Вторые блюда",
        variants=[variant("280/250 гр", 360)],
        ingredients="Гречневая или пшеничная лапша с овощами, грибами и курицей в овощном соусе.",
        position=4,
    ),
    entry(
        name="Пад тай",
        menu_group="Основное меню",
        section="Вторые блюда",
        variants=[variant("400 гр", 490)],
        ingredients="Рисовая лапша, курица, яйцо, сладкий перец, морковь, чеснок, зелень.",
        position=5,
    ),
    entry(
        name="Сэндвич с курицей",
        menu_group="Основное меню",
        section="Фаст-фуд",
        variants=[variant("220 гр", 270)],
        ingredients="Тосты, соус тар-тар, курица, маринованные огурцы, томаты, красный лук, салат айсберг.",
        position=1,
    ),
    entry(
        name="Сэндвич чикенчиз",
        menu_group="Основное меню",
        section="Фаст-фуд",
        variants=[variant("240 гр", 270)],
        ingredients="Тройной сэндвич с копченой грудкой, сыром моцарелла и медово-горчичным соусом.",
        position=2,
    ),
    entry(
        name="Мясной сэндвич",
        menu_group="Основное меню",
        section="Фаст-фуд",
        variants=[variant("290 гр", 410)],
        ingredients="Булочка чиабатта с говядиной, беконом и сыром чеддер.",
        position=3,
    ),
    entry(
        name="Чизбургер",
        menu_group="Основное меню",
        section="Фаст-фуд",
        variants=[variant("140 гр", 280)],
        ingredients="Булочка бриошь, котлета из говядины, салат айсберг, томаты, горчица, маринованные огурцы.",
        position=4,
    ),
    entry(
        name="Ранч чикен-ролл",
        menu_group="Основное меню",
        section="Фаст-фуд",
        variants=[variant("210 гр", 300)],
        ingredients="Сырная тортилья, копченая курица, моцарелла, томаты, соус ранч.",
        position=5,
    ),
    entry(
        name="Шаверма чикен-классик",
        menu_group="Основное меню",
        section="Фаст-фуд",
        variants=[variant("340 гр", 350)],
        ingredients="Куриные наггетсы, маринованные огурцы, капуста, сыр моцарелла и тортилья, соус на выбор.",
        position=6,
    ),
    entry(
        name="Картофель фри",
        menu_group="Основное меню",
        section="Фаст-фуд",
        variants=[variant("100 гр", 150)],
        position=7,
    ),
    entry(
        name="Наггетсы",
        menu_group="Основное меню",
        section="Фаст-фуд",
        variants=[variant("100 гр", 220)],
        position=8,
    ),
    entry(
        name="Бургер Хашбраун",
        menu_group="Основное меню",
        section="Закрытые корейские бургеры",
        variants=[variant("220 гр", 300)],
        ingredients="Булочка бриошь, колбаска, хашбраун, маринованные огурцы, копченая грудка, сырный соус.",
        position=1,
    ),
    entry(
        name="Цезарь бургер",
        menu_group="Основное меню",
        section="Закрытые корейские бургеры",
        variants=[variant("190 гр", 300)],
        ingredients="Булочка бриошь, грудка цыпленка, томаты, айсберг, чеддер, пармезан, соус цезарь.",
        position=2,
    ),
    entry(
        name="Кранч бургер",
        menu_group="Основное меню",
        section="Закрытые корейские бургеры",
        variants=[variant("250 гр", 280)],
        ingredients="Булочка бриошь, говяжья котлета, яйцо, томаты, маринованные огурцы, соус BBQ, лук пай.",
        position=3,
    ),
    entry(
        name="Бургер Тейсти",
        menu_group="Основное меню",
        section="Закрытые корейские бургеры",
        variants=[variant("200 гр", 320)],
        ingredients="Булочка бриошь, говяжья котлета, томаты, маринованные огурцы, чеддер, соус тейсти.",
        position=4,
    ),
    entry(
        name="Ананас-терияки бургер",
        menu_group="Основное меню",
        section="Закрытые корейские бургеры",
        variants=[variant("220 гр", 350)],
        ingredients="Булочка бриошь, грудка цыпленка, моцарелла, ананас, красный лук, соус терияки.",
        position=5,
    ),
    entry(
        name="Классический хот-дог",
        menu_group="Основное меню",
        section="Хот-доги",
        variants=[variant("140 гр", 250)],
        ingredients="Булочка, кетчуп, горчица, маринованные огурцы, колбаска, лук пай.",
        position=1,
    ),
    entry(
        name="Французский хот-дог",
        menu_group="Основное меню",
        section="Хот-доги",
        variants=[variant("120 гр", 230)],
        ingredients="Закрытая булочка, колбаска, кетчуп, горчица.",
        position=2,
    ),
    entry(
        name="Маргарита",
        menu_group="Пицца",
        section="Пицца",
        variants=[variant("450 гр", 480)],
        ingredients="Моцарелла, соус на основе томатов, базилик.",
        is_featured=True,
        position=1,
    ),
    entry(
        name="4 сыра",
        menu_group="Пицца",
        section="Пицца",
        variants=[variant("510 гр", 620)],
        ingredients="Моцарелла, белый соус на основе рикотты, чеддер, пармезан, дор блю.",
        position=2,
    ),
    entry(
        name="Курица / Грибы",
        menu_group="Пицца",
        section="Пицца",
        variants=[variant("530 гр", 550)],
        ingredients="Моцарелла, белый соус, курица, шампиньоны.",
        position=3,
    ),
    entry(
        name="Мясная",
        menu_group="Пицца",
        section="Пицца",
        variants=[variant("530 гр", 540)],
        ingredients="Моцарелла, белый соус, ветчина, бекон, курица, пепперони.",
        position=4,
    ),
    entry(
        name="Ранч",
        menu_group="Пицца",
        section="Пицца",
        variants=[variant("480 гр", 480)],
        ingredients="Моцарелла, соус ранч, курица, копченая грудка.",
        position=5,
    ),
    entry(
        name="Пепперони",
        menu_group="Пицца",
        section="Пицца",
        variants=[variant("520 гр", 580)],
        ingredients="Моцарелла, томатный соус, пепперони, базилик.",
        position=6,
    ),
    entry(
        name="Пицца чикен пармеджано",
        menu_group="Пицца",
        section="Пицца",
        variants=[variant("480 гр", 630)],
        ingredients="Моцарелла, белый соус, курица, томаты, пармезан.",
        position=7,
    ),
    entry(
        name="Пицца Чикен Карри",
        menu_group="Пицца",
        section="Пицца",
        variants=[variant("540 гр", 530)],
        ingredients="Моцарелла, соус карри, курица, сладкий перец, чеддер, красный лук.",
        position=8,
    ),
    entry(
        name="Пицца «Бургерная»",
        menu_group="Пицца",
        section="Пицца",
        variants=[variant("630 гр", 620)],
        ingredients="Моцарелла, соус тейсти, говяжий фарш, томаты, красный лук.",
        position=9,
    ),
    entry(
        name="Закрытая пицца Дачная",
        menu_group="Пицца",
        section="Закрытая пицца",
        variants=[variant("280 гр", 300)],
        ingredients="Копченая грудка, картофель фри, моцарелла, шампиньоны, чесночный соус.",
        position=10,
    ),
    entry(
        name="Закрытая пицца по-абхазски",
        menu_group="Пицца",
        section="Закрытая пицца",
        variants=[variant("220 гр", 250)],
        ingredients="Охотничьи колбаски, пепперони, моцарелла, маринованные огурцы, соус аджика.",
        position=11,
    ),
    entry(
        name="Закрытая пицца сборная",
        menu_group="Пицца",
        section="Закрытая пицца",
        variants=[variant("260 гр", 230)],
        ingredients="Шпинат, колбаски, сыр моцарелла, томаты, огурцы, маринованные огурцы.",
        position=12,
    ),
    entry(
        name="Маргарита 40 см",
        menu_group="Пицца",
        section="Большая пицца",
        variants=[variant("750 гр", 690)],
        ingredients="Моцарелла, соус из томатов, базилик.",
        position=13,
    ),
    entry(
        name="4 сыра 40 см",
        menu_group="Пицца",
        section="Большая пицца",
        variants=[variant("780 гр", 900)],
        ingredients="Моцарелла, белый соус, чеддер, пармезан, дор блю.",
        position=14,
    ),
    entry(
        name="Пепперони 40 см",
        menu_group="Пицца",
        section="Большая пицца",
        variants=[variant("820 гр", 900)],
        ingredients="Моцарелла, томатный соус, колбаски пепперони, базилик.",
        position=15,
    ),
    entry(
        name="Мясная 40 см",
        menu_group="Пицца",
        section="Большая пицца",
        variants=[variant("800 гр", 900)],
        ingredients="Моцарелла, белый соус, ветчина, бекон, курица, пепперони.",
        position=16,
    ),
    entry(
        name="Шаверма",
        menu_group="Студенческое меню",
        section="Студенческое меню",
        variants=[variant("340 гр", 320)],
        ingredients="Куриные наггетсы, маринованные огурцы, капуста, сыр моцарелла в тортилье, соус на выбор.",
        position=1,
    ),
    entry(
        name="Ролл с омлетом",
        menu_group="Студенческое меню",
        section="Студенческое меню",
        variants=[variant("200 гр", 190)],
        ingredients="Омлет с сыром пармезан и ветчиной в мексиканской тортилье.",
        position=2,
    ),
    entry(
        name="Сборная пицца",
        menu_group="Студенческое меню",
        section="Студенческое меню",
        variants=[variant("260 гр", 190)],
        ingredients="Закрытая пицца с курицей, колбасками, сыром моцарелла, свежими овощами и огурцами.",
        position=3,
    ),
    entry(
        name="Закрытый бургер Тейсти",
        menu_group="Студенческое меню",
        section="Студенческое меню",
        variants=[variant("200 гр", 280)],
        ingredients="Булочка бриошь, говяжья котлета, томаты, маринованные огурцы, чеддер, соус тейсти.",
        position=4,
    ),
    entry(
        name="Закрытый Цезарь бургер",
        menu_group="Студенческое меню",
        section="Студенческое меню",
        variants=[variant("200 гр", 270)],
        ingredients="Булочка бриошь, грудка цыпленка, томаты, айсберг, сыр чеддер, пармезан, соус цезарь.",
        position=5,
    ),
    entry(
        name="Вок с курицей",
        menu_group="Студенческое меню",
        section="Студенческое меню",
        variants=[variant("200 гр", 330)],
        ingredients="Гречневая или пшеничная лапша с овощами, грибами и курицей в овощном соусе.",
        position=6,
    ),
    entry(
        name="Наггетсы",
        menu_group="Студенческое меню",
        section="Студенческое меню",
        variants=[variant("100 гр", 190)],
        position=7,
    ),
    entry(
        name="Картофель фри",
        menu_group="Студенческое меню",
        section="Студенческое меню",
        variants=[variant("100 гр", 120)],
        position=8,
    ),
    entry(
        name="Вишнёвый пирожок",
        menu_group="Студенческое меню",
        section="Студенческое меню",
        variants=[variant("85 гр", 90)],
        position=9,
    ),
    entry(
        name="Фундучное какао",
        menu_group="Студенческое меню",
        section="Студенческое меню",
        variants=[variant("350 мл", 230)],
        position=10,
    ),
    entry(
        name="Кола",
        menu_group="Студенческое меню",
        section="Студенческое меню",
        variants=[variant("400 мл", 140)],
        position=11,
    ),
    entry(
        name="Фильтр-кофе",
        menu_group="Студенческое меню",
        section="Студенческое меню",
        variants=[variant("200 мл", 180)],
        ingredients="Черный кофе, заваренный в капельной кофеварке.",
        position=12,
    ),
    entry(
        name="Айс бабл баунти",
        menu_group="Весеннее меню",
        section="Весеннее меню",
        variants=[variant("375 мл", 350)],
        ingredients="Кокосовые кубики, кокосовое молоко, шоколадный сироп, эспрессо, лед.",
        tags=["seasonal"],
        is_featured=True,
        position=1,
    ),
    entry(
        name="Барбарисовый лимонад",
        menu_group="Весеннее меню",
        section="Весеннее меню",
        variants=[variant("500 мл", 280)],
        ingredients="Содовая, барбарисовый сироп, лимонный сок, лед.",
        tags=["seasonal"],
        position=2,
    ),
    entry(
        name="Горячий шоколад с мятой",
        menu_group="Весеннее меню",
        section="Весеннее меню",
        variants=[variant("280 мл", 300)],
        ingredients="Топпинг мята, шоколад молочный, молоко, белый шоколадный сироп.",
        tags=["seasonal"],
        position=3,
    ),
    entry(
        name="Раф лимонный пирог",
        menu_group="Весеннее меню",
        section="Весеннее меню",
        variants=[variant("300 мл", 300)],
        ingredients="Сливки, молоко, эспрессо, соус лимонный пирог, лимонная стружка.",
        tags=["seasonal"],
        position=4,
    ),
    entry(
        name="Ромашка-черника",
        menu_group="Весеннее меню",
        section="Весеннее меню",
        variants=[variant("350 мл", 280)],
        ingredients="Ромашковый чай, лаванда, соус черника, мята.",
        tags=["seasonal"],
        position=5,
    ),
    entry(
        name="Юдзу шприц",
        menu_group="Весеннее меню",
        section="Весеннее меню",
        variants=[variant("300 мл", 380)],
        ingredients="Безалкогольное шампанское, юдзу соус, лимонный сок, лед.",
        tags=["seasonal"],
        position=6,
    ),
    entry(
        name="Грибной сэндвич с баклажанами",
        menu_group="Весеннее меню",
        section="Весеннее меню",
        variants=[variant("390 гр", 450)],
        ingredients="Чиабатта, баклажаны, шампиньоны, грудка цыпленка, моцарелла, сливки.",
        tags=["seasonal"],
        position=7,
    ),
    entry(
        name="Рисовая каша с манго",
        menu_group="Весеннее меню",
        section="Весеннее меню",
        variants=[variant("350 гр", 380)],
        ingredients="Рисовая каша на кокосовом молоке с манго и лепестками миндаля.",
        tags=["seasonal"],
        position=8,
    ),
    entry(
        name="Сырный рамен",
        menu_group="Весеннее меню",
        section="Весеннее меню",
        variants=[variant("550 гр", 400)],
        ingredients="Сливочно-говяжий бульон, рисовая лапша, грудка цыпленка, колбаски чоризо, сыр, зеленый лук.",
        tags=["seasonal"],
        position=9,
    ),
    entry(
        name="Салат с нутом по-гречески",
        menu_group="Весеннее меню",
        section="Весеннее меню",
        variants=[variant("230 гр", 350)],
        ingredients="Нут, томаты, сыр фета, болгарский перец, красный лук, медово-оливковый соус.",
        tags=["seasonal"],
        position=10,
    ),
    entry(
        name="Паста Тейсти",
        menu_group="Весеннее меню",
        section="Весеннее меню",
        variants=[variant("320 гр", 550)],
        ingredients="Паста фузилли, фарш говяжий, маринованные огурцы, красный лук, сыр чеддер, томатный соус.",
        tags=["seasonal"],
        position=11,
    ),
    entry(
        name="Пибимпап",
        menu_group="Весеннее меню",
        section="Весеннее меню",
        variants=[variant("360 гр", 600)],
        ingredients="Рис, семга, огурцы, перец болгарский, красная жареная капуста, корейская морковь, яйцо, сырный соус.",
        tags=["seasonal"],
        position=12,
    ),
    entry(
        name="Пирожное карамельное",
        menu_group="Весеннее меню",
        section="Весеннее меню",
        variants=[variant("70 гр", 180)],
        ingredients="Печенье савоярди, прослоенное карамельным кремом.",
        tags=["seasonal"],
        position=13,
    ),
    entry(
        name="Пирожное шоколад-гречка",
        menu_group="Весеннее меню",
        section="Весеннее меню",
        variants=[variant("70 гр", 180)],
        ingredients="Печенье савоярди, шоколадный крем, попкорн из гречки.",
        tags=["seasonal"],
        position=14,
    ),
    entry(
        name="Слойка с вишней / с грушей",
        menu_group="Весеннее меню",
        section="Весеннее меню",
        variants=[variant("125/120 гр", 200)],
        ingredients="Сдобное дрожжевое тесто с начинкой на выбор.",
        tags=["seasonal"],
        position=15,
    ),
]


async def seed_demo_menu() -> None:
    async with AsyncSession(engine) as session:
        existing_items = await session.exec(select(MenuEntryRecord.id))
        if existing_items.first() is not None:
            return

        known_groups: set[str] = set()
        menu_collections: list[MenuCollectionRecord] = []
        for item in DEMO_MENU_ITEMS:
            menu_group = str(item["menu_group"])
            if menu_group in known_groups:
                continue
            known_groups.add(menu_group)
            menu_collections.append(MenuCollectionRecord(name=menu_group))

        session.add_all(menu_collections)
        session.add_all(MenuEntryRecord.model_validate(item) for item in DEMO_MENU_ITEMS)
        await session.commit()
        invalidate_menu_render_cache()


async def backfill_menu_translations() -> None:
    async with AsyncSession(engine) as session:
        result = await session.exec(select(MenuEntryRecord))
        items = list(result.all())
        has_changes = False

        for item in items:
            is_untouched_seed = (
                (item.id or 0) <= len(DEMO_MENU_ITEMS)
                and abs((item.updated_at - item.created_at).total_seconds()) < 1
            )
            legacy_name_en = translate_menu_text_legacy(item.name)
            legacy_description_en = translate_menu_text_legacy(item.description)
            legacy_ingredients_en = translate_menu_text_legacy(item.ingredients)
            previous_name_en = translate_menu_text_previous(item.name)
            previous_description_en = translate_menu_text_previous(item.description)
            previous_ingredients_en = translate_menu_text_previous(item.ingredients)
            normalized_name_en = translate_menu_text(item.name, context="name")
            normalized_description_en = translate_menu_text(
                item.description,
                context="description",
            )
            normalized_ingredients_en = translate_menu_text(
                item.ingredients,
                context="ingredients",
            )

            if (
                not item.name_en.strip()
                or item.name_en == legacy_name_en
                or item.name_en == previous_name_en
                or is_untouched_seed
            ):
                item.name_en = normalized_name_en
                has_changes = True
            if (
                not item.description_en.strip()
                or item.description_en == legacy_description_en
                or item.description_en == previous_description_en
                or is_untouched_seed
            ):
                item.description_en = normalized_description_en
                has_changes = True
            if (
                not item.ingredients_en.strip()
                or item.ingredients_en == legacy_ingredients_en
                or item.ingredients_en == previous_ingredients_en
                or is_untouched_seed
            ):
                item.ingredients_en = normalized_ingredients_en
                has_changes = True

        if not has_changes:
            return

        session.add_all(items)
        await session.commit()
        invalidate_menu_render_cache()
