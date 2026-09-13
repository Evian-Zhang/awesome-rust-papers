import unittest

from pathlib import Path

from awesome_rust_papers import RELATION_KINDS, load_collection


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CollectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.collection = load_collection(PROJECT_ROOT)

    def test_loads_every_info_file(self):
        expected = len(list((PROJECT_ROOT / "infos").glob("*.json")))
        self.assertEqual(len(self.collection.papers), expected)
        self.assertEqual(set(self.collection.by_id), {paper.id for paper in self.collection.papers})

    def test_vocabularies_are_derived_from_papers(self):
        papers = self.collection.papers
        self.assertEqual(
            self.collection.categories(),
            tuple(sorted({value for paper in papers for value in paper.category})),
        )
        self.assertEqual(
            self.collection.tags(),
            tuple(sorted({value for paper in papers for value in paper.tag})),
        )
        self.assertEqual(
            self.collection.venues(),
            tuple(sorted({paper.venue for paper in papers if paper.venue})),
        )

    def test_resolves_relation_values_and_builds_reverse_edges(self):
        source = next(paper for paper in self.collection.papers if paper.relation("reference"))
        target = next(edge for edge in self.collection.outgoing(source, "reference") if edge.is_internal)

        self.assertIn(source, self.collection.incoming(target.paper_id, "reference"))
        self.assertEqual(self.collection.resolve(target.value).paper_id, target.paper_id)

    def test_all_relation_kinds_share_one_interface(self):
        paper = self.collection.papers[0]
        self.assertEqual(set(paper.relations), set(RELATION_KINDS))
        for kind in RELATION_KINDS:
            self.assertEqual(tuple(self.collection.outgoing(paper, kind)), self.collection.outgoing(paper.id, kind))


if __name__ == "__main__":
    unittest.main()
