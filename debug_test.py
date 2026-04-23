import sys
sys.path.insert(0, 'D:/KG_project/Final4.14')

with open('D:/KG_project/Final4.14/test_log.txt', 'w') as f:
    f.write("Starting test\n")
    f.flush()

    try:
        from unittest.mock import MagicMock
        from src.experts.safety_expert import SafetyExpert
        from src.experts.production_expert import ProductionExpert
        from src.experts.quality_expert import QualityExpert
        from src.allocator.batch_scorer import BatchScorer
        from src.allocator.entropy_weight import EntropyWeightCalculator

        f.write("All imports succeeded\n")
        f.flush()

        # Test 1: Markdown-wrapped JSON
        f.write("\nTest 1: Markdown-wrapped JSON\n")
        f.flush()
        mock_llm = MagicMock()
        mock_llm.generate.return_value = '```json\n{"H1_visibility": 1.0, "H2_space_limitation": 1.5, "H3_object_movement": 2.0, "H4_ergonomic_impact": 1.0, "H5_repetitiveness": 0.5, "S1_high_voltage": 2.0, "S2_chemical_reagent": 0.5, "S3_fire_explosion": 0.5, "S4_human_injury": 1.0, "Lh_human_loss": 1.5, "Lr_robot_loss": 1.0}\n```'
        expert = SafetyExpert(mock_llm)
        result = expert.score("Battery壳体")
        f.write(f"  H1_visibility: {result['H1_visibility']} (expected 1.0)\n")
        f.write(f"  H2_space_limitation: {result['H2_space_limitation']} (expected 1.5)\n")
        f.write(f"  S1_high_voltage: {result['S1_high_voltage']} (expected 2.0)\n")
        f.flush()
        assert result['H1_visibility'] == 1.0, f"Failed: got {result['H1_visibility']}"
        assert result['H2_space_limitation'] == 1.5, f"Failed: got {result['H2_space_limitation']}"
        assert result['S1_high_voltage'] == 2.0, f"Failed: got {result['S1_high_voltage']}"
        f.write("  PASSED\n")
        f.flush()

        # Test 2: Three experts with different scores
        f.write("\nTest 2: Three experts with different scores\n")
        f.flush()
        mock_llm = MagicMock()
        def side_effect(prompt):
            if "安全工程师" in prompt:
                return '{"H1_visibility": 1.0, "H2_space_limitation": 1.5, "H3_object_movement": 2.0, "H4_ergonomic_impact": 1.0, "H5_repetitiveness": 0.5, "S1_high_voltage": 2.0, "S2_chemical_reagent": 0.5, "S3_fire_explosion": 0.5, "S4_human_injury": 1.0, "Lh_human_loss": 1.5, "Lr_robot_loss": 1.0}'
            elif "生产工艺工程师" in prompt:
                return '{"H1_visibility": 2.0, "H2_space_limitation": 2.5, "H3_object_movement": 1.0, "H4_ergonomic_impact": 1.5, "H5_repetitiveness": 0.5, "S1_high_voltage": 1.0, "S2_chemical_reagent": 1.5, "S3_fire_explosion": 0.5, "S4_human_injury": 2.0, "Lh_human_loss": 1.0, "Lr_robot_loss": 2.0}'
            else:
                return '{"H1_visibility": 0.5, "H2_space_limitation": 1.0, "H3_object_movement": 1.5, "H4_ergonomic_impact": 0.5, "H5_repetitiveness": 1.0, "S1_high_voltage": 1.5, "S2_chemical_reagent": 0.5, "S3_fire_explosion": 1.0, "S4_human_injury": 0.5, "Lh_human_loss": 2.0, "Lr_robot_loss": 0.5}'
        mock_llm.generate.side_effect = side_effect
        scorer = BatchScorer(mock_llm, None)
        result = scorer.score_component("Battery壳体", "EV-500")

        f.write(f"  Expert A H1: {result['expert_A_scores']['H1_visibility']} (expected 1.0)\n")
        f.write(f"  Expert B H1: {result['expert_B_scores']['H1_visibility']} (expected 2.0)\n")
        f.write(f"  Expert C H1: {result['expert_C_scores']['H1_visibility']} (expected 0.5)\n")
        f.write(f"  h_score: {result['h_score']}\n")
        f.write(f"  s_score: {result['s_score']}\n")
        f.write(f"  as_score: {result['as_score']}\n")
        f.flush()
        assert result['expert_A_scores']['H1_visibility'] == 1.0
        assert result['expert_B_scores']['H1_visibility'] == 2.0
        assert result['expert_C_scores']['H1_visibility'] == 0.5
        f.write("  PASSED\n")
        f.flush()

        # Test 3: Verify scores are NOT all 1.5
        f.write("\nTest 3: Verify scores differ from uniform 1.5 case\n")
        f.flush()
        calc = EntropyWeightCalculator()
        expert_scores = [
            {'H1_visibility': 1.0, 'H2_space_limitation': 1.5, 'H3_object_movement': 2.0, 'H4_ergonomic_impact': 1.0, 'H5_repetitiveness': 0.5, 'S1_high_voltage': 2.0, 'S2_chemical_reagent': 0.5, 'S3_fire_explosion': 0.5, 'S4_human_injury': 1.0, 'Lh_human_loss': 1.5, 'Lr_robot_loss': 1.0},
            {'H1_visibility': 2.0, 'H2_space_limitation': 2.5, 'H3_object_movement': 1.0, 'H4_ergonomic_impact': 1.5, 'H5_repetitiveness': 0.5, 'S1_high_voltage': 1.0, 'S2_chemical_reagent': 1.5, 'S3_fire_explosion': 0.5, 'S4_human_injury': 2.0, 'Lh_human_loss': 1.0, 'Lr_robot_loss': 2.0},
            {'H1_visibility': 0.5, 'H2_space_limitation': 1.0, 'H3_object_movement': 1.5, 'H4_ergonomic_impact': 0.5, 'H5_repetitiveness': 1.0, 'S1_high_voltage': 1.5, 'S2_chemical_reagent': 0.5, 'S3_fire_explosion': 1.0, 'S4_human_injury': 0.5, 'Lh_human_loss': 2.0, 'Lr_robot_loss': 0.5},
        ]
        result = calc.calculate_final_scores(expert_scores)
        f.write(f"  h_score: {result['h_score']}\n")
        f.write(f"  s_score: {result['s_score']}\n")
        f.write(f"  as_score: {result['as_score']}\n")
        f.flush()
        assert result['h_score'] != 0.5, "h_score should not be 0.5 with different expert scores"
        assert result['as_score'] != 0.5, "as_score should not be 0.5 with different expert scores"
        f.write("  PASSED\n")
        f.flush()

        f.write("\n" + "="*50 + "\n")
        f.write("ALL TESTS PASSED!\n")
        f.write("Three-expert scoring system is working correctly.\n")
        f.write("="*50 + "\n")
        f.flush()

    except Exception as e:
        import traceback
        f.write(f"Exception: {e}\n")
        f.write(traceback.format_exc())
        f.flush()