"""Unit tests for node graph construction helpers."""

import unittest

from OV_Libs.ProjStoreLib.node_graph_builder import NodeGraphBuilder


class TestNodeGraphBuilder(unittest.TestCase):
    """Validate node creation, linking rules, and pipeline compatibility."""

    def test_add_node_with_custom_slots(self):
        builder = NodeGraphBuilder()

        node = builder.add_node("merge", "Merge", input_count=3, output_count=2)

        self.assertEqual(node["id"], "merge")
        self.assertEqual(node["type"], "Merge")
        self.assertEqual(node["input_ports"], ["input_0", "input_1", "input_2"])
        self.assertEqual(node["output_ports"], ["output_0", "output_1"])
        self.assertEqual(node["linked_inputs"], [None, None, None])
        self.assertEqual(node["linked_outputs"], [[], []])

    def test_connect_enforces_single_input_slot(self):
        builder = NodeGraphBuilder()
        builder.add_node("a", "Input", input_count=0, output_count=1)
        builder.add_node("b", "Input", input_count=0, output_count=1)
        builder.add_node("merge", "Merge", input_count=1, output_count=1)

        builder.connect("a", "merge", to_input_index=0)

        with self.assertRaises(ValueError) as context:
            builder.connect("b", "merge", to_input_index=0)

        self.assertIn("Input slot already connected", str(context.exception))

    def test_connect_chain_builds_linked_list(self):
        builder = NodeGraphBuilder()
        builder.add_node("n1", "Input", input_count=0, output_count=1)
        builder.add_node("n2", "Filter", input_count=1, output_count=1)
        builder.add_node("n3", "Output", input_count=1, output_count=0)

        created = builder.connect_chain(["n1", "n2", "n3"])

        self.assertEqual(len(created), 2)
        self.assertEqual(builder.get_connections()[0]["from_node"], "n1")
        self.assertEqual(builder.get_connections()[1]["to_node"], "n3")

    def test_build_pipeline_from_builder_graph(self):
        builder = NodeGraphBuilder()

        builder.add_node("in", "Input", input_count=0, output_count=1)
        builder.add_node("left", "FilterA", input_count=1, output_count=1)
        builder.add_node("right", "FilterB", input_count=1, output_count=1)
        builder.add_node("merge", "Merge", input_count=2, output_count=1)
        builder.add_node("out", "Output", input_count=1, output_count=0)

        builder.connect("in", "left", to_input_index=0)
        builder.connect("in", "right", to_input_index=0)
        builder.connect_many_to_input(["left", "right"], "merge")
        builder.connect("merge", "out", to_input_index=0)

        pipeline, is_valid, errors = builder.build_pipeline()

        self.assertTrue(is_valid, msg=f"Errors: {errors}")
        self.assertEqual(pipeline["max_stage"], 3)
        self.assertEqual(pipeline["stages"][1]["can_parallelize"], True)


if __name__ == "__main__":
    unittest.main()
