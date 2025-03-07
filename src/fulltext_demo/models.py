import django.db.models

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.query import QuerySet

from django.db.models import (
    ForeignKey, DateTimeField, NullBooleanField, ManyToManyField,
    TextField, CharField, PositiveSmallIntegerField
)


class Item(django.db.models.Model):
    name = CharField(max_length=1000)
    description = TextField()
    rating = PositiveSmallIntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(10)]
    )

    class Meta:
        indexes = [
            # GinIndex(SearchVector("name", "description", config="russian"), name='name_desc_gin'),
            GinIndex(SearchVector("name", config="russian"), name='name_gin'),
            GinIndex(SearchVector("description", config="russian"), name='desc_gin')
        ]

    @classmethod
    def ranked_search(cls, query: str) -> QuerySet:
        """
        Perform fulltext search in item name and description. Annotate each item with `sortorder`,
        calcualted as balanced combination of 70% query match (ts_rank) and 30% item rating.


        Parameter `query` is in websearch_to_tsquery postgres format. See https://www.postgresql.org/docs/current/textsearch-controls.html#TEXTSEARCH-PARSING-QUERIES for reference.

        Example: "drill OR hammer"
        """
        language = 'russian'

        return cls.objects.extra(
            select = {
                "sortorder": (f"""
                    ts_rank(
                        to_tsvector('{language}', coalesce(description, '')) ||
                        to_tsvector('{language}', coalesce(name, '')),
                        websearch_to_tsquery('{language}', %s)
                    ) * 70"""  # Fulltext match affects 70% of sortorder
                    "+ rating * 0.01 * 30"  # Item rating affects 30% of sortorder
                )
            },
            select_params = [query],

            where = [
                (
                    # f"to_tsvector('{language}', coalesce(description, '')) || to_tsvector('{language}', coalesce(name, '')) "
                    f"to_tsvector('{language}', coalesce(description, '')) "
                    f"@@ (websearch_to_tsquery('{language}', %s)) = true"
                    " OR "
                    f"to_tsvector('{language}', coalesce(name, '')) "
                    f"@@ (websearch_to_tsquery('{language}', %s)) = true"
                )
            ],
            params = [query, query],
        )
