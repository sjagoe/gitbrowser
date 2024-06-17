import unittest


from .__main__ import pagination


class Test(unittest.TestCase):

    def test_pagination_1(self):
        # Given
        item_count = 20
        visible_item_count = 15
        selected_ix = 0

        # When
        page, pages, page_start_ix = pagination(
            item_count, visible_item_count, selected_ix)

        # Then
        self.assertEqual(page, 0)
        self.assertEqual(pages, 2)
        self.assertEqual(page_start_ix, 0)

    def test_pagination_2(self):
        # Given
        item_count = 20
        visible_item_count = 15
        selected_ix = 5

        # When
        page, pages, page_start_ix = pagination(
            item_count, visible_item_count, selected_ix)

        # Then
        self.assertEqual(page, 0)
        self.assertEqual(pages, 2)
        self.assertEqual(page_start_ix, 0)

    def test_pagination_3(self):
        # Given
        item_count = 20
        visible_item_count = 15
        selected_ix = 14

        # When
        page, pages, page_start_ix = pagination(
            item_count, visible_item_count, selected_ix)

        # Then
        self.assertEqual(page, 0)
        self.assertEqual(pages, 2)
        self.assertEqual(page_start_ix, 0)

    def test_pagination_4(self):
        # Given
        item_count = 20
        visible_item_count = 15
        selected_ix = 15

        # When
        page, pages, page_start_ix = pagination(
            item_count, visible_item_count, selected_ix)

        # Then
        self.assertEqual(page, 1)
        self.assertEqual(pages, 2)
        self.assertEqual(page_start_ix, 15)

    def test_pagination_5(self):
        # Given
        item_count = 20
        visible_item_count = 15
        selected_ix = 16

        # When
        page, pages, page_start_ix = pagination(
            item_count, visible_item_count, selected_ix)

        # Then
        self.assertEqual(page, 1)
        self.assertEqual(pages, 2)
        self.assertEqual(page_start_ix, 15)

    def test_pagination_6(self):
        # Given
        item_count = 20
        visible_item_count = 15
        selected_ix = 18

        # When
        page, pages, page_start_ix = pagination(
            item_count, visible_item_count, selected_ix)

        # Then
        self.assertEqual(page, 1)
        self.assertEqual(pages, 2)
        self.assertEqual(page_start_ix, 15)

    def test_pagination_7(self):
        # Given
        item_count = 20
        visible_item_count = 15
        selected_ix = 19

        # When
        page, pages, page_start_ix = pagination(
            item_count, visible_item_count, selected_ix)

        # Then
        self.assertEqual(page, 1)
        self.assertEqual(pages, 2)
        self.assertEqual(page_start_ix, 15)
