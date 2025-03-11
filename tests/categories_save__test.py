import django.test

from fulltext_demo.models import Category


class CategoriesSaveTest(django.test.TestCase):
    """ Category.ancestors should be updated when Category.parent changes. """

    def setUp(self):
        # GIVEN 6 categoreis organized in a tree
        self.machines = Category.objects.create(name='machines')
        self.wheeled =     Category.objects.create(name='wheeled', parent=self.machines)
        self.track =       Category.objects.create(name='track', parent=self.machines)

        self.tools =    Category.objects.create(name='tools')
        self.mixers =      Category.objects.create(name='mixers', parent=self.tools)
        self.concrete_mixers =  Category.objects.create(name='concrete mixers', parent=self.mixers)

    def test_cats_save(self):
        # WHEN self.tools parent changed and saved
        # THEN ancestry tree should be updated in 12 queries:
        # SAVEPOINT
        # * First tools.save() with updated parent (but no ancestors yet)
        #   UPDATE "fulltext_demo_category" SET "name" = 'tools', "description" = '', "parent_id" = 2, "ancestors" = '{}'::integer[] WHERE "fulltext_demo_category"."id" = 4
        # * Category.objects.select_related('parent').prefetch_related('direct_kids')
        #   Two queries - regular select and prefetch select
        #   SELECT "fulltext_demo_category"."id", ... FROM "fulltext_demo_category"
        #   SELECT "fulltext_demo_category"."id", ... FROM "fulltext_demo_category" WHERE "fulltext_demo_category"."parent_id" IN (1, 2, 3, 5, 4)
        # * mixers.save() with updates ancestors
        #   SAVEPOINT
        #   UPDATE "fulltext_demo_category" SET "name" = 'mixers', "description" = '', "parent_id" = 4, "ancestors" = ARRAY[4,2,1]::integer[] WHERE "fulltext_demo_category"."id" = 5
        #   RELEASE SAVEPOINT
        # * concrete_mixers.save() with updates ancestors
        #   SAVEPOINT
        #   UPDATE "fulltext_demo_category" SET "name" = 'concrete mixers', "description" = '', "parent_id" = 5, "ancestors" = ARRAY[5,4,2,1]::integer[] WHERE "fulltext_demo_category"."id" = 6
        #   RELEASE SAVEPOINT
        # * second tools.save() with updated ancestors
        #   UPDATE "fulltext_demo_category" SET "name" = 'tools', "description" = '', "parent_id" = 2, "ancestors" = ARRAY[2,1]::integer[] WHERE "fulltext_demo_category"."id" = 4
        # RELEASE SAVEPOINT
        with self.assertNumQueries(12):
            self.tools.parent = self.wheeled
            self.tools.save()

        # AND tools ancestors should be updated
        assert set(self.tools.ancestors) == {self.machines.id, self.wheeled.id}

        # AND mixers ancestors should be updated
        assert (
            set(Category.objects.get(id=self.mixers.id).ancestors)
            ==
            {self.machines.id, self.wheeled.id, self.tools.id}
        )

        # AND concrete_mixers ancestors should be updated
        assert (
            set(Category.objects.get(id=self.concrete_mixers.id).ancestors)
            ==
            {self.machines.id, self.wheeled.id, self.tools.id, self.mixers.id}
        )

