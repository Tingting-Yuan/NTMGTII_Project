import heapq
import sys

class Graph:
    def __init__(self):
        # Store vertices as {node: {neighbor: cost}}
        self.vertices = {}
        
    def add_vertex(self, name, edges):
        """Add a vertex and its edges to the graph."""
        self.vertices[name] = edges
    
    def shortest_path(self, start, finish):
        """
        Compute the shortest path using Dijkstra's algorithm.
        Returns the path as a list of nodes from start to finish.
        If the node does not exist, returns None.
        """
        
        distances = {}      # Distance from start to each node
        previous = {}       # Previous node in optimal path
        nodes = []          # Priority queue (min-heap)

        # Initialize all vertices
        for vertex in self.vertices:
            if vertex == start:
                distances[vertex] = 0
                heapq.heappush(nodes, [0, vertex])
            else:
                distances[vertex] = sys.maxsize
                heapq.heappush(nodes, [sys.maxsize, vertex])
            previous[vertex] = None
        
        # Main Dijkstra loop

        
        # If the destination is unreachable, return distance table
        return distances
    
    def __str__(self):
        """Return the string representation of the graph."""
        return str(self.vertices)


if __name__ == '__main__':
    g = Graph()
    g.add_vertex('A', {'B': 7, 'C': 8})
    g.add_vertex('B', {'A': 7, 'F': 2})
    g.add_vertex('C', {'A': 8, 'F': 6, 'G': 4})
    g.add_vertex('D', {'F': 8})
    g.add_vertex('E', {'H': 1})
    g.add_vertex('F', {'B': 2, 'C': 6, 'D': 8, 'G': 9, 'H': 3})
    g.add_vertex('G', {'C': 4, 'F': 9})
    g.add_vertex('H', {'E': 1, 'F': 3})

    print(g.shortest_path('A', 'H'))  # Expected output: ['A', 'B', 'F', 'H']
    print(g.shortest_path('A', 'K'))  # Expected output: None
