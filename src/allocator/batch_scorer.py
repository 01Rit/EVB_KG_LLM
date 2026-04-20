from typing import Dict, List, Optional
from src.experts import SafetyExpert, ProductionExpert, QualityExpert
from src.allocator.entropy_weight import EntropyWeightCalculator
from src.allocator.as_calculator import ASCalculator
from src.kg.client import Neo4jClient
from src.utils.llm_client import LLMClient
import json
import logging

logger = logging.getLogger(__name__)


class BatchScorer:
    def __init__(self, llm_client: LLMClient, neo4j_client: Optional[Neo4jClient] = None):
        self.llm = llm_client
        self.neo4j = neo4j_client
        self.safety_expert = SafetyExpert(llm_client)
        self.production_expert = ProductionExpert(llm_client)
        self.quality_expert = QualityExpert(llm_client)
        self.entropy_calc = EntropyWeightCalculator()
        self.as_calc = ASCalculator()

    def score_component(self, component_name: str, battery_model: str = '',
                        context: str = '') -> Dict:
        expert_a_scores = self.safety_expert.score(component_name, context)
        expert_b_scores = self.production_expert.score(component_name, context)
        expert_c_scores = self.quality_expert.score(component_name, context)

        all_scores = [expert_a_scores, expert_b_scores, expert_c_scores]
        final_scores = self.entropy_calc.calculate_final_scores(all_scores)

        human_loss = final_scores['human_loss']
        robot_loss = final_scores['robot_loss']

        assignee = self.as_calc.determine_assignee(
            final_scores['as_score'],
            human_loss=human_loss,
            robot_loss=robot_loss
        )

        t_expert_scores = [
            {'H_T': expert_a_scores.get('T_T', 1.5)},
            {'S_T': expert_b_scores.get('T_T', 1.5)},
            {'Q_T': expert_c_scores.get('T_T', 1.5)}
        ]
        t_result = self.entropy_calc.calculate_t_score(t_expert_scores)

        result = {
            'component': component_name,
            'battery_model': battery_model,
            'expert_A_scores': expert_a_scores,
            'expert_B_scores': expert_b_scores,
            'expert_C_scores': expert_c_scores,
            'h_score': final_scores['h_score'],
            's_score': final_scores['s_score'],
            'as_score': final_scores['as_score'],
            'human_loss': human_loss,
            'robot_loss': robot_loss,
            'loss_diff': final_scores['loss_diff'],
            'assignee': assignee,
            'time_score': t_result['t_score'],
            'h_time_factor': t_result['h_time_factor'],
            's_time_factor': t_result['s_time_factor'],
            'q_time_factor': t_result['q_time_factor'],
        }

        if self.neo4j:
            self._update_neo4j_node(result)

        return result

    def score_all_l1_components(self, battery_model: str = '') -> List[Dict]:
        if not self.neo4j:
            raise RuntimeError("Neo4j client required for batch scoring")

        components = self.neo4j.get_all_components(battery_model=battery_model, top_k=100)
        l1_components = [c for c in components if c.get('source_type') in ('manual', 'pdf', 'csv', 'txt') or not c.get('source_type')]

        results = []
        for comp in l1_components:
            try:
                result = self.score_component(
                    comp.get('name', ''),
                    comp.get('battery_model', ''),
                    ''
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to score component {comp.get('name')}: {e}")

        return results

    def _update_neo4j_node(self, score_data: Dict) -> None:
        if not self.neo4j:
            return

        component_name = score_data['component']
        properties = {
            'expert_A_scores': json.dumps(score_data['expert_A_scores']),
            'expert_B_scores': json.dumps(score_data['expert_B_scores']),
            'expert_C_scores': json.dumps(score_data['expert_C_scores']),
            'h_weighted_score': score_data['h_score'],
            's_weighted_score': score_data['s_score'],
            'as_score': score_data['as_score'],
            'human_loss': score_data['human_loss'],
            'robot_loss': score_data['robot_loss'],
            'loss_diff': score_data['loss_diff'],
            'assignee': score_data['assignee'],
            'time_score': score_data.get('time_score', 0),
            'h_time_factor': score_data.get('h_time_factor', 1.5),
            's_time_factor': score_data.get('s_time_factor', 1.5),
            'q_time_factor': score_data.get('q_time_factor', 1.5),
        }

        try:
            self.neo4j.update_component_properties(component_name, properties)
            logger.info(f"Updated Neo4j node for {component_name}")
        except Exception as e:
            logger.error(f"Failed to update Neo4j node {component_name}: {e}")