import django.db.models

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.query import QuerySet

from django.db.models import (
    ForeignKey, DateTimeField, NullBooleanField, ManyToManyField,
    TextField, CharField, PositiveSmallIntegerField, CASCADE
)


class Item(django.db.models.Model):
    name = CharField(max_length=1000)
    description = TextField()
    rating = PositiveSmallIntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(10)]
    )
    categories = ManyToManyField('Category', related_name='items')

    class Meta:
        indexes = [
            # GinIndex(SearchVector("name", "description", config="russian"), name='name_desc_gin'),
            GinIndex(SearchVector("name", config="russian"), name='name_gin'),
            GinIndex(SearchVector("description", config="russian"), name='desc_gin')
        ]

    @classmethod
    def pg_ranked_search(
        cls,

        # Query string in websearch_to_tsquery postgres format. See
        # https://www.postgresql.org/docs/current/textsearch-controls.html#TEXTSEARCH-PARSING-QUERIES
        # for reference.
        # Example: "drill OR hammer"
        query_str: str
    ) -> QuerySet:
        """
        Perform postgres fulltext search in item name and description. Annotate each item
        with `sortorder`, calcualted as balanced combination of 70% query match (ts_rank)
        and 30% item rating.
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
            select_params = [query_str],

            where = [(
                # f"to_tsvector('{language}', coalesce(description, '')) || to_tsvector('{language}', coalesce(name, '')) "
                f"to_tsvector('{language}', coalesce(description, '')) "
                f"@@ (websearch_to_tsquery('{language}', %s)) = true"
                " OR "
                f"to_tsvector('{language}', coalesce(name, '')) "
                f"@@ (websearch_to_tsquery('{language}', %s)) = true"
            )],
            params = [query_str, query_str],
        ).order_by('-sortorder')


class Category(django.db.models.Model):
    name = CharField(max_length=1000)
    description = TextField()
    parent = ForeignKey('self', null=True, blank=True, on_delete=CASCADE)
