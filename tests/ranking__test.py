

test_data = [
    # Two almost identical items, only differ in rating
    {
        "name": "Плохой Водоструйный Очиститель",
        "description": "Высоконапорный водоструйный очиститель для обслуживания строительной техники, способный удалять затвердевшие остатки бетона.",
        "rating": 2
    },
    {
        "name": "Хороший Водоструйный Очиститель",
        "description": "Высоконапорный водоструйный очиститель для обслуживания строительной техники, способный удалять затвердевшие остатки бетона.",
        "rating": 8
    },

    # Everything else
    {
        "name": "Экскаватор",
        "description": "Тяжелый экскаватор с кабиной, вращающейся на 360 градусов, предназначенный для копки глубоких фундаментов и траншей в сложных грунтовых условиях.",
        "rating": 7
    },
    {
        "name": "Бетоносмеситель",
        "description": "Компактный бетоносмеситель емкостью 500 литров, идеально подходящий для небольших строительных проектов и легкой транспортировки.",
        "rating": 4
    },
    {
        "name": "Сваебой",
        "description": "Гидравлический сваебой с технологией снижения шума, идеально подходящий для городских строительных площадок для забивания стальных свай в грунт.",
        "rating": 9
    },
    {
        "name": "Башенный кран",
        "description": "Универсальный башенный кран с вылетом 50 метров, способный поднимать до 10 тонн для строительства высотных зданий.",
        "rating": 6
    },
    {
        "name": "Бульдозер",
        "description": "Прочный бульдозер с усиленным отвалом и системой GPS-навигации для точных земляных работ.",
        "rating": 8
    },
    {
        "name": "Резак для арматуры",
        "description": "Переносной резак для арматуры с электродвигателем, предназначенный для резки стальных арматурных стержней толщиной до 25 мм.",
        "rating": 3
    },
    {
        "name": "Погрузчик",
        "description": "Многотерrainный колесный погрузчик с грузоподъемностью 3 тонны, оптимизированный для загрузки гравия и песка в неровных строительных условиях.",
        "rating": 10
    },
    {
        "name": "Асфальтоукладчик",
        "description": "Самоходный асфальтоукладчик с регулируемой шириной выглаживающей плиты, используемый для эффективной укладки гладких дорожных покрытий.",
        "rating": 5
    },
    {
        "name": "Строительная вышка",
        "description": "Мобильная строительная вышка с регулируемой высотой, обеспечивающая безопасный доступ для рабочих на фасадах зданий до 12 метров.",
        "rating": 7
    }
]


def sortorder_ranking__test():
    from pgtest.models import Item

    query = 'Очиститель'

    Item.ranked_search('').order_by('-sortorder').values()

    # Results in full text ranked search:
    final_query = '''
    SELECT (ts_rank(to_tsvector('russian', coalesce(description, '')) || to_tsvector('russian', coalesce(name, '')), websearch_to_tsquery('russian', 'good OR drill')) * 70+ rating * 0.01 * 30) AS "sortorder",
        "pgtest_item"."id",
        "pgtest_item"."name",
        "pgtest_item"."description",
        "pgtest_item"."rating"
    FROM "pgtest_item"
    WHERE (to_tsvector('russian', coalesce(description, '')) @@ (websearch_to_tsquery('russian', 'good OR drill')) = true OR to_tsvector('russian', coalesce(name, '')) @@ (websearch_to_tsquery('russian', 'good OR drill')) = true)
    ORDER BY 1 DESC
    '''
