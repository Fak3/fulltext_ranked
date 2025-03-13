import pytest
import unittest

from django.db.models import Q
from model_bakery.baker import make

from fulltext_demo.models import Item, Category


@pytest.mark.django_db
def sortorder_ranking__test():
    """ PostgreSQL fulltext query for items should order high-rated items higher. """

    # GIVEN 6 categoreis organized in a tree
    machines = Category.objects.create(name='machines')
    wheeled =     Category.objects.create(name='wheeled', parent=machines)
    track =       Category.objects.create(name='track', parent=machines)

    tools =    Category.objects.create(name='tools')
    mixers =      Category.objects.create(name='mixers', parent=tools)
    cleaners =    Category.objects.create(name='cleaners', parent=tools)

    # AND water cleaner with low rating in category tools
    make(Item, categories=[tools],  **{
        "name": "Хороший Водоструйный Очиститель",
        "description": """
            Высоконапорный водоструйный очиститель для обслуживания строительной техники, способный удалять затвердевшие остатки бетона.
            В хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем хорошем состоянии.
            Хороший Очиститель
            Хороший Очиститель
            Хороший Очиститель
            Хороший Очиститель
        """,
        "rating": 2
    })
    # AND water cleaner with high rating in category cleaners
    make(Item, categories=[cleaners],  **{
        "name": "Хороший Водоструйный Очиститель",
        "description": "Высоконапорный водоструйный очиститель для обслуживания строительной техники, способный удалять затвердевшие остатки бетона.",
        "rating": 8
    })

    # AND high-ranked sand cleaner in category cleaners
    make(Item, categories=[cleaners],  **{
        "name": "Хороший Пескоструйный Очиститель",
        "description": "Высоконапорный пескоструйный очиститель для обслуживания строительной техники, способный удалять затвердевшие остатки бетона.",
        "rating": 8
    })

    # AND cleaner in machines category
    make(Item, categories=[machines],  **{
        "name": "Очиститель канав на базе трактора",
        "description": "Хороший очиститель",
        "rating": 9
    })

    # AND cutter in tools category
    make(Item, categories=[tools],  **{
        "name": "Резак для арматуры",
        "description": "Переносной резак для арматуры с электродвигателем, предназначенный для резки стальных арматурных стержней толщиной до 25 мм.",
        "rating": 3
    })

    # AND excavator
    make(Item, categories=[track],  **{
        "name": "Экскаватор",
        "description": "Тяжелый экскаватор с кабиной, вращающейся на 360 градусов, предназначенный для копки глубоких фундаментов и траншей в сложных грунтовых условиях.",
        "rating": 7
    })

    #
    #     # Everything else
    #     {
    #         "name": "Бетоносмеситель",
    #         "description": "Компактный бетоносмеситель емкостью 500 литров, идеально подходящий для небольших строительных проектов и легкой транспортировки.",
    #         "rating": 4
    #     },
    #     {
    #         "name": "Сваебой",
    #         "description": "Гидравлический сваебой с технологией снижения шума, идеально подходящий для городских строительных площадок для забивания стальных свай в грунт.",
    #         "rating": 9
    #     },
    #     {
    #         "name": "Башенный кран",
    #         "description": "Универсальный башенный кран с вылетом 50 метров, способный поднимать до 10 тонн для строительства высотных зданий.",
    #         "rating": 6
    #     },
    #     {
    #         "name": "Бульдозер",
    #         "description": "Прочный бульдозер с усиленным отвалом и системой GPS-навигации для точных земляных работ.",
    #         "rating": 8
    #     },
    #     {
    #         "name": "Погрузчик",
    #         "description": "Многотерrainный колесный погрузчик с грузоподъемностью 3 тонны, оптимизированный для загрузки гравия и песка в неровных строительных условиях.",
    #         "rating": 10
    #     },
    #     {
    #         "name": "Асфальтоукладчик",
    #         "description": "Самоходный асфальтоукладчик с регулируемой шириной выглаживающей плиты, используемый для эффективной укладки гладких дорожных покрытий.",
    #         "rating": 5
    #     },
    #     {
    #         "name": "Строительная вышка",
    #         "description": "Мобильная строительная вышка с регулируемой высотой, обеспечивающая безопасный доступ для рабочих на фасадах зданий до 12 метров.",
    #         "rating": 7
    #     }
    # ]


    # WHEN fulltext query for "Good cleaner" in "tools" category and
    # subcategories is executed
    items = Item.pg_ranked_search('Хороший Очиститель').filter(
        # Items in "tools" category
        Q(categories=tools)
        |
        # Items in any subcategory of "tools"
        Q(categories__ancestors__contains=[tools.id])
    )

    # THEN cleaner with higher rating is sorted higher
    assert (
        list(items.values('sortorder', 'name', 'rating'))
        ==
        [
            {
                'name': 'Хороший Водоструйный Очиститель',
                'rating': 8,
                'sortorder': 6.500000037252903,
            },
            {
                'name': 'Хороший Пескоструйный Очиститель',
                'rating': 8,
                'sortorder': 6.500000037252903,
            },
            {
                'name': 'Хороший Водоструйный Очиститель',
                'rating': 2,
                'sortorder': 3.500000037252903,
            },
        ]
    )

    # Results in full text ranked search:
    final_query = '''
    SELECT (ts_rank_cd(to_tsvector('russian', coalesce(fulltext_demo_item.name, '')), websearch_to_tsquery('russian', 'Хороший Очиститель')) * 50 + rating * 0.01 * 50) AS "sortorder",
        "fulltext_demo_item"."name",
        "fulltext_demo_item"."rating"
    FROM "fulltext_demo_item"
    INNER JOIN "fulltext_demo_item_categories"
        ON ("fulltext_demo_item"."id" = "fulltext_demo_item_categories"."item_id")
    INNER JOIN "fulltext_demo_category"
        ON ("fulltext_demo_item_categories"."category_id" = "fulltext_demo_category"."id")
    WHERE ((to_tsvector('russian', coalesce(fulltext_demo_item.description, '')) @@ (websearch_to_tsquery('russian', 'Хороший Очиститель')) = true OR to_tsvector('russian', coalesce(fulltext_demo_item.name, '')) @@ (websearch_to_tsquery('russian', 'Хороший Очиститель')) = true)
    AND ("fulltext_demo_item_categories"."category_id" = 5
        OR "fulltext_demo_category"."ancestors" @> (ARRAY[5])::integer[])) ORDER BY 1 DESC LIMIT 21;
    '''
    #
    # SELECT *
    # FROM "fulltext_demo_category"
    # WHERE ("fulltext_demo_category"."ancestors" @> (ARRAY[5])::integer[]) LIMIT 21;
