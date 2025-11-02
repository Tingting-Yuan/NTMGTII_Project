import unittest
from dijkstra import Graph


class Graph_Test(unittest.TestCase):

    def setUp(self):
        """Create two graphs and one empty graph for testing."""
        # Graph 1: medium connected graph
        self.graph1 = Graph()
        self.graph1.add_vertex('A', {'B': 7, 'C': 8})
        self.graph1.add_vertex('B', {'A': 7, 'F': 2})
        self.graph1.add_vertex('C', {'A': 8, 'F': 6, 'G': 4})
        self.graph1.add_vertex('D', {'F': 8})
        self.graph1.add_vertex('E', {'H': 1})
        self.graph1.add_vertex('F', {'B': 2, 'C': 6, 'D': 8, 'G': 9, 'H': 3})
        self.graph1.add_vertex('G', {'C': 4, 'F': 9})
        self.graph1.add_vertex('H', {'E': 1, 'F': 3})

        # Graph 2: small simple graph
        self.graph2 = Graph()
        self.graph2.add_vertex('A', {'B': 1})
        self.graph2.add_vertex('B', {'A': 1, 'C': 2})
        self.graph2.add_vertex('C', {'B': 2})


    # -------- Graph 1 Tests --------
    def test_graph1_path_A_to_H(self):
        """Shortest path A→H in Graph 1."""
        result = self.graph1.shortest_path('A', 'H')
        self.assertEqual(result, ['A', 'B', 'F', 'H'])

    def test_graph1_nonexistent_target(self):
        """If target node does not exist, return None."""
        result = self.graph1.shortest_path('A', 'Z')
        self.assertIsNone(result)

    def test_graph1_nonexistent_source(self):
        """If source node does not exist, return None."""
        result = self.graph1.shortest_path('Z', 'A')
        self.assertIsNone(result)

    # -------- Graph 2 Tests --------
    def test_graph2_A_to_C(self):
        """Shortest path A→C in Graph 2 (via B)."""
        result = self.graph2.shortest_path('A', 'C')
        self.assertEqual(result, ['A', 'B', 'C'])

    def test_graph2_same_node(self):
        """Path from A→A should just return ['A']."""
        result = self.graph2.shortest_path('A', 'A')
        self.assertEqual(result, ['A'])


if __name__ == "__main__":
    unittest.main()
