import django.db.models

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.query import QuerySet
from django.db import transaction


from django.db.models import (
    ForeignKey, DateTimeField, NullBooleanField, ManyToManyField,
    TextField, CharField, PositiveSmallIntegerField, CASCADE, AutoField, IntegerField
)


class Item(django.db.models.Model):
    name = CharField(max_length=1000)
    description = TextField()
    rating = PositiveSmallIntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(10)]
    )
    categories = ManyToManyField('Category', related_name='items')
    # flat_categories = ManyToManyField('Category', related_name='deep_items')

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
        Perform postgres fulltext search in item name. Annotate each item
        with `sortorder`, calcualted as balanced combination of 50% query match (ts_rank)
        and 50% item rating.
        """
        language = 'russian'

        return cls.objects.extra(
            select = {
                "sortorder": (
                    # ts_rank ranges from 0.0 to 1.0
                    # f"""
                    # ts_rank(
                    #     to_tsvector('{language}', coalesce(name, '')) ||
                    #     to_tsvector('{language}', coalesce(description, '')),
                    #     websearch_to_tsquery('{language}', %s)
                    # )
                    # """
                    f"""
                    ts_rank_cd(
                        to_tsvector('{language}', coalesce(fulltext_demo_item.name, '')),
                        websearch_to_tsquery('{language}', %s)
                    ) * 50
                    """ # Fulltext match affects 50% of sortorder

                    # TODO: ranking description easily hijacked by repetition of terms by
                    # item author.
                    # # ts_rank_cd (cover density) considers the proximity of lexemes to each other
                    # f"""
                    # +
                    # ts_rank_cd(
                    #     to_tsvector('{language}', coalesce(description, '')),
                    #     websearch_to_tsquery('{language}', %s)
                    # ) * 10
                    # """
                    "+ rating * 0.01 * 50"  # Item rating affects 50% of sortorder
                )
            },
            select_params = [query_str],

            where = [(
                # f"to_tsvector('{language}', coalesce(description, '')) || to_tsvector('{language}', coalesce(name, '')) "
                f"to_tsvector('{language}', coalesce(fulltext_demo_item.description, '')) "
                f"@@ (websearch_to_tsquery('{language}', %s)) = true"
                " OR "
                f"to_tsvector('{language}', coalesce(fulltext_demo_item.name, '')) "
                f"@@ (websearch_to_tsquery('{language}', %s)) = true"
            )],
            params = [query_str, query_str],
        ).order_by('-sortorder')


class Category(django.db.models.Model):
    # id = AutoField(primary_key=True)
    name = CharField(max_length=1000)
    description = TextField()
    parent = ForeignKey('self', related_name='direct_kids', null=True, blank=True, on_delete=CASCADE)

    # Ancestors are automatically updated in save() when parent changes.
    #
    # Used in queries for items in all subcategories:
    # >> items = Item.objects.filter(
    # ..     Q(categories=tools) | Q(categories__ancestors__contains=[tools.id])
    # .. )
    #
    # TODO: Would index do anything on ancestors?
    # explain analyze SELECT * FROM "fulltext_demo_category"
    # WHERE ("fulltext_demo_category"."ancestors" @> (ARRAY[5])::integer[]);
    ancestors = ArrayField(IntegerField(), null=True, blank=True)

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._old_parent_id = self.parent_id

    def __str__(self):
        return f'{self.name}'

    def save(self, *a, **kw):
        """ Save, updating self.ancestors """

        with transaction.atomic():
            # Save myself with new parent, but still old ancestors.
            super().save(*a, **kw)

            if not kw.get('force_insert') and self._old_parent_id == self.parent_id:
                # Force_insert is False, this object already exists in database.
                # Parent hasn't been changed, skip updating ancestors.
                return

            cats: dict[int, Category] = Category.map()

            # Update my ancestors.
            self.ancestors = [x.id for x in cats[self.id].ancestors_list]

            # Update ancestors of all my descendants.
            for cat in cats[self.id].descendants_list:
                # print(cat, cats[cat.id].ancestors_list)
                cat.ancestors = [x.id for x in cats[cat.id].ancestors_list]
                cat.save()

            # Save myself with new ancestors.
            super().save(*a, **dict(kw, force_insert=False))

    @classmethod
    def map(cls) -> dict[int, "Category"]:
        """
        Return dict id -> Category. Annotate each category with ancestors_list
        and descendants_list. Only takes two SELECT queries. Used in save() method
        to update ancestors when parent changes.
        """
        # Two queries: regular SELECT and prefetch SELECT
        # We can actually build it in one query, but with prefetch_related it is simpler.
        cats = {cat.id: cat for cat in cls.objects.prefetch_related('direct_kids')}

        def iter_ancestors(cat):
            while cat := cats.get(cats[cat.id].parent_id):
                yield cat

        def iter_descendants(cat):
            for kid in cat.direct_kids.all():
                yield kid
                yield from iter_descendants(cats[kid.id])

        for cat in cats.values():
            cat.ancestors_list = list(iter_ancestors(cat))
            cat.descendants_list = list(iter_descendants(cat))

        return cats
