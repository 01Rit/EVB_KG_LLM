# Three-Expert Scoring System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement three-expert scoring system for L1 battery disassembly components with entropy-weighted AS scoring and Neo4j persistence.

**Architecture:**
- Three expert LLM prompt modules (safety, production, quality) score H1-H5, S1-S4, and damage factors
- Entropy weight calculator processes expert scores into final H, S, AS scores
- Batch scorer pre-computes and persists scores to Neo4j nodes
- API schemas extended to return new scoring fields

**Tech Stack:** Python FastAPI, Neo4j, OpenAI LLM, pytest

---

## File Structure

```
src/
├── experts/
│   ├── __init__.py                    # (create)
│   ├── base_expert.py                 # (create) Abstract base with shared scoring logic
│   ├── safety_expert.py               # (create) Safety engineer scoring
│   ├── production_expert.py           # (create) Production engineer scoring
│   └── quality_expert.py              # (create) Quality inspector scoring
├── allocator/
│   ├── entropy_weight.py              # (create) Entropy weight calculation
│   ├── batch_scorer.py                # (create) Batch scoring service
│   └── as_calculator.py               # (modify) Fix determine_assignee logic
├── kg/
│   └── client.py                      # (modify) Add update_component_properties method
src/api/
├── schemas.py                         # (modify) Add scoring fields to Step schema

tests/
├── experts/
│   ├── __init__.py                    # (create)
│   ├── test_base_expert.py            # (create)
│   ├── test_safety_expert.py          # (create)
│   ├── test_production_expert.py      # (create)
│   └── test_quality_expert.py         # (create)
├── allocator/
│   ├── test_entropy_weight.py         # (create)
│   └── test_batch_scorer.py           # (create)
```

---

## Task 1: Create Expert Base Class

**Files:**
- Create: `src/experts/__init__.py`
- Create: `src/experts/base_expert.py`
- Create: `tests/experts/__init__.py`
- Create: `tests/experts/test_base_expert.py`

- [ ] **Step 1: Write failing test**

```python
# tests/experts/test_base_expert.py
import pytest
from src.experts.base_expert import BaseExpert

def test_base_expert_abstract():
    with pytest.raises(TypeError):
        BaseExpert()

def test_factor_count():
    assert len(BaseExpert.H_FACTORS) == 5
    assert len(BaseExpert.S_FACTORS) == 4
    assert len(BaseExpert.D_FACTORS) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/experts/test_base_expert.py -v`
Expected: FAIL - No module named 'src.experts'

- [ ] **Step 3: Create `src/experts/__init__.py`**

```python
from src.experts.base_expert import BaseExpert
from src.experts.safety_expert import SafetyExpert
from src.experts.production_expert import ProductionExpert
from src.experts.quality_expert import QualityExpert

__all__ = ['BaseExpert', 'SafetyExpert', 'ProductionExpert', 'QualityExpert']
```

- [ ] **Step 4: Create `src/experts/base_expert.py`**

```python
from abc import ABC, abstractmethod
from typing import Dict, List
from src.utils.llm_client import LLMClient
import json
import logging

logger = logging.getLogger(__name__)


class BaseExpert(ABC):
    H_FACTORS = ['H1_visibility', 'H2_space_limitation', 'H3_object_movement',
                 'H4_ergonomic_impact', 'H5_repetitiveness']

    S_FACTORS = ['S1_high_voltage', 'S2_chemical_reagent', 'S3_fire_explosion', 'S4_human_injury']

    D_FACTORS = ['Lh_human_loss', 'Lr_robot_loss']

    FACTOR_DESCRIPTIONS = {
        'H1_visibility': '0=完全可见, 3=完全遮挡',
        'H2_space_limitation': '0=宽敞, 3=完全限制',
        'H3_object_movement': '0=≤1kg, 3=≥15kg',
        'H4_ergonomic_impact': '0=舒适, 3=极度不适',
        'H5_repetitiveness': '0=<5次, 3=>30次',
        'S1_high_voltage': '0=无风险, 3=极高风险',
        'S2_chemical_reagent': '0=无风险, 3=高风险',
        'S3_fire_explosion': '0=无风险, 3=高风险',
        'S4_human_injury': '0=无风险, 3=高风险',
        'Lh_human_loss': '0=无损失, 3=严重损伤',
        'Lr_robot_loss': '0=无损失, 3=严重损伤',
    }

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    @property
    @abstractmethod
    def expert_name(self) -> str:
        """Return expert name."""
        pass

    @property
    @abstractmethod
    def expert_role(self) -> str:
        """Return expert role description."""
        pass

    def build_scoring_prompt(self, component_name: str, context: str = '') -> str:
        factor_list = '\n'.join([f"- {f}: {self.FACTOR_DESCRIPTIONS[f]}" for f in self.H_FACTORS + self.S_FACTORS + self.D_FACTORS])

        return f'''你是{self.expert_name}（{self.expert_role}）。

评估部件 {component_name} 的拆卸评分因素。

上下文信息：{context if context else '无'}

请对以下因素给出0-3的评分：
{factor_list}

返回JSON格式（所有值必须是0-3的整数或浮点数）：
{{"H1_visibility": 0-3, "H2_space_limitation": 0-3, "H3_object_movement": 0-3, "H4_ergonomic_impact": 0-3, "H5_repetitiveness": 0-3, "S1_high_voltage": 0-3, "S2_chemical_reagent": 0-3, "S3_fire_explosion": 0-3, "S4_human_injury": 0-3, "Lh_human_loss": 0-3, "Lr_robot_loss": 0-3}}
'''

    def score(self, component_name: str, context: str = '') -> Dict[str, float]:
        prompt = self.build_scoring_prompt(component_name, context)
        try:
            result = self.llm.generate(prompt)
            scores = json.loads(result)
            validated = {}
            all_factors = self.H_FACTORS + self.S_FACTORS + self.D_FACTORS
            for f in all_factors:
                val = scores.get(f, 1.5)
                validated[f] = max(0.0, min(3.0, float(val)))
            return validated
        except Exception as e:
            logger.error(f"{self.expert_name} scoring failed: {e}")
            return {f: 1.5 for f in self.H_FACTORS + self.S_FACTORS + self.D_FACTORS}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/experts/test_base_expert.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/experts/__init__.py src/experts/base_expert.py tests/experts/__init__.py tests/experts/test_base_expert.py
git commit -m "feat: add BaseExpert abstract class for three-expert scoring"
```

---

## Task 2: Create Safety Expert

**Files:**
- Create: `src/experts/safety_expert.py`
- Create: `tests/experts/test_safety_expert.py`

- [ ] **Step 1: Write failing test**

```python
# tests/experts/test_safety_expert.py
import pytest
from src.experts.safety_expert import SafetyExpert
from unittest.mock import MagicMock

def test_safety_expert_properties():
    mock_llm = MagicMock()
    expert = SafetyExpert(mock_llm)
    assert expert.expert_name == "安全工程师"
    assert expert.expert_role == "负责评估拆卸过程中的安全风险"
    assert 'S1_high_voltage' in expert.H_FACTORS or 'S1_high_voltage' in expert.S_FACTORS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/experts/test_safety_expert.py -v`
Expected: FAIL - No module named 'src.experts.safety_expert'

- [ ] **Step 3: Create `src/experts/safety_expert.py`**

```python
from src.experts.base_expert import BaseExpert
from src.utils.llm_client import LLMClient


class SafetyExpert(BaseExpert):
    @property
    def expert_name(self) -> str:
        return "安全工程师"

    @property
    def expert_role(self) -> str:
        return "负责评估拆卸过程中的安全风险"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/experts/test_safety_expert.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/experts/safety_expert.py tests/experts/test_safety_expert.py
git commit -m "feat: add SafetyExpert for safety factor scoring"
```

---

## Task 3: Create Production Expert

**Files:**
- Create: `src/experts/production_expert.py`
- Create: `tests/experts/test_production_expert.py`

- [ ] **Step 1: Write failing test**

```python
# tests/experts/test_production_expert.py
import pytest
from src.experts.production_expert import ProductionExpert
from unittest.mock import MagicMock

def test_production_expert_properties():
    mock_llm = MagicMock()
    expert = ProductionExpert(mock_llm)
    assert expert.expert_name == "生产工艺工程师"
    assert expert.expert_role == "负责评估拆卸工艺的复杂度和效率"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/experts/test_production_expert.py -v`
Expected: FAIL

- [ ] **Step 3: Create `src/experts/production_expert.py`**

```python
from src.experts.base_expert import BaseExpert
from src.utils.llm_client import LLMClient


class ProductionExpert(BaseExpert):
    @property
    def expert_name(self) -> str:
        return "生产工艺工程师"

    @property
    def expert_role(self) -> str:
        return "负责评估拆卸工艺的复杂度和效率"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/experts/test_production_expert.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/experts/production_expert.py tests/experts/test_production_expert.py
git commit -m "feat: add ProductionExpert for production factor scoring"
```

---

## Task 4: Create Quality Expert

**Files:**
- Create: `src/experts/quality_expert.py`
- Create: `tests/experts/test_quality_expert.py`

- [ ] **Step 1: Write failing test**

```python
# tests/experts/test_quality_expert.py
import pytest
from src.experts.quality_expert import QualityExpert
from unittest.mock import MagicMock

def test_quality_expert_properties():
    mock_llm = MagicMock()
    expert = QualityExpert(mock_llm)
    assert expert.expert_name == "质量检测专家"
    assert expert.expert_role == "负责评估拆卸过程中的质量控制和损伤风险"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/experts/test_quality_expert.py -v`
Expected: FAIL

- [ ] **Step 3: Create `src/experts/quality_expert.py`**

```python
from src.experts.base_expert import BaseExpert
from src.utils.llm_client import LLMClient


class QualityExpert(BaseExpert):
    @property
    def expert_name(self) -> str:
        return "质量检测专家"

    @property
    def expert_role(self) -> str:
        return "负责评估拆卸过程中的质量控制和损伤风险"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/experts/test_quality_expert.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/experts/quality_expert.py tests/experts/test_quality_expert.py
git commit -m "feat: add QualityExpert for quality factor scoring"
```

---

## Task 5: Create Entropy Weight Calculator

**Files:**
- Create: `src/allocator/entropy_weight.py`
- Create: `tests/allocator/test_entropy_weight.py`

- [ ] **Step 1: Write failing test**

```python
# tests/allocator/test_entropy_weight.py
import pytest
import numpy as np
from src.allocator.entropy_weight import EntropyWeightCalculator

def test_entropy_weight_calculator_init():
    calc = EntropyWeightCalculator()
    assert calc is not None

def test_normalize_scores():
    calc = EntropyWeightCalculator()
    scores = [1.0, 2.0, 3.0]
    normalized = calc._normalize(scores)
    assert abs(sum(normalized) - 1.0) < 1e-6

def test_entropy_calculation():
    calc = EntropyWeightCalculator()
    p = [0.5, 0.5]
    e = calc._calculate_entropy(p)
    assert 0 <= e <= 1

def test_weight_from_expert_scores():
    calc = EntropyWeightCalculator()
    expert_scores = [
        {'H1': 1.0, 'H2': 2.0, 'H3': 1.5},
        {'H1': 2.0, 'H2': 1.0, 'H3': 2.5},
        {'H1': 1.5, 'H2': 1.5, 'H3': 2.0},
    ]
    weights = calc.calculate_weights(expert_scores, factor_names=['H1', 'H2', 'H3'])
    assert len(weights) == 3
    assert abs(sum(weights) - 1.0) < 1e-6

def test_final_h_score():
    calc = EntropyWeightCalculator()
    expert_scores = [
        {'H1': 1.0, 'H2': 2.0, 'H3': 1.0, 'H4': 2.0, 'H5': 1.5,
         'S1': 1.0, 'S2': 0.5, 'S3': 0.5, 'S4': 1.0},
        {'H1': 2.0, 'H2': 1.0, 'H3': 2.0, 'H4': 1.0, 'H5': 2.5,
         'S1': 2.0, 'S2': 1.0, 'S3': 1.0, 'S4': 2.0},
        {'H1': 1.5, 'H2': 1.5, 'H3': 1.5, 'H4': 1.5, 'H5': 2.0,
         'S1': 1.5, 'S2': 0.75, 'S3': 0.75, 'S4': 1.5},
    ]
    result = calc.calculate_final_scores(expert_scores)
    assert 0 <= result['h_score'] <= 1
    assert 0 <= result['s_score'] <= 1
    assert 0 <= result['as_score'] <= 1
    assert 'human_loss' in result
    assert 'robot_loss' in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/allocator/test_entropy_weight.py -v`
Expected: FAIL - No module named 'src.allocator.entropy_weight'

- [ ] **Step 3: Create `src/allocator/entropy_weight.py`**

```python
import numpy as np
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class EntropyWeightCalculator:
    H_FACTOR_NAMES = ['H1_visibility', 'H2_space_limitation', 'H3_object_movement',
                      'H4_ergonomic_impact', 'H5_repetitiveness']

    S_FACTOR_NAMES = ['S1_high_voltage', 'S2_chemical_reagent', 'S3_fire_explosion', 'S4_human_injury']

    D_FACTOR_NAMES = ['Lh_human_loss', 'Lr_robot_loss']

    def __init__(self, k: float = 1.0):
        self.k = k

    def _normalize(self, values: List[float]) -> List[float]:
        total = sum(values)
        if total == 0:
            return [1.0 / len(values)] * len(values)
        return [v / total for v in values]

    def _calculate_entropy(self, p: List[float]) -> float:
        m = len(p)
        k = 1.0 / np.log(m) if m > 1 else 1.0
        entropy = 0.0
        for pi in p:
            if pi > 0:
                entropy -= pi * np.log(pi)
        return k * entropy

    def calculate_weights(self, expert_scores: List[Dict[str, float]],
                          factor_names: List[str]) -> List[float]:
        if len(expert_scores) < 2:
            return [1.0 / len(factor_names)] * len(factor_names)

        factor_values = []
        for fname in factor_names:
            values = [max(0.001, scores.get(fname, 0.0)) for scores in expert_scores]
            normalized = self._normalize(values)
            entropy = self._calculate_entropy(normalized)
            factor_values.append(1.0 - entropy)

        total = sum(factor_values)
        if total == 0:
            return [1.0 / len(factor_names)] * len(factor_names)

        return [fv / total for fv in factor_values]

    def calculate_final_scores(self, expert_scores: List[Dict[str, float]]) -> Dict[str, float]:
        h_weights = self.calculate_weights(expert_scores, self.H_FACTOR_NAMES)
        s_weights = self.calculate_weights(expert_scores, self.S_FACTOR_NAMES)

        h_raw_scores = []
        s_raw_scores = []
        human_losses = []
        robot_losses = []

        for scores in expert_scores:
            h_vals = [max(0.0, min(3.0, scores.get(f, 1.5))) for f in self.H_FACTOR_NAMES]
            s_vals = [max(0.0, min(3.0, scores.get(f, 1.5))) for f in self.S_FACTOR_NAMES]
            h_raw_scores.append(h_vals)
            s_raw_scores.append(s_vals)
            human_losses.append(max(0.0, min(3.0, scores.get('Lh_human_loss', 1.5))))
            robot_losses.append(max(0.0, min(3.0, scores.get('Lr_robot_loss', 1.5))))

        avg_h = np.mean(h_raw_scores, axis=0)
        avg_s = np.mean(s_raw_scores, axis=0)

        h_weighted = sum(v * w for v, w in zip(avg_h, h_weights))
        s_weighted = sum(v * w for v, w in zip(avg_s, s_weights))

        h_score = round(h_weighted / 3.0, 3)
        s_score = round(s_weighted / 3.0, 3)
        as_score = round(0.5 * (h_score + s_score), 3)

        avg_human_loss = round(np.mean(human_losses), 3)
        avg_robot_loss = round(np.mean(robot_losses), 3)

        return {
            'h_score': h_score,
            's_score': s_score,
            'as_score': as_score,
            'human_loss': avg_human_loss,
            'robot_loss': avg_robot_loss,
            'loss_diff': round(avg_human_loss - avg_robot_loss, 3),
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/allocator/test_entropy_weight.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/allocator/entropy_weight.py tests/allocator/test_entropy_weight.py
git commit -m "feat: add EntropyWeightCalculator for three-expert scoring"
```

---

## Task 6: Create Batch Scorer Service

**Files:**
- Create: `src/allocator/batch_scorer.py`
- Create: `tests/allocator/test_batch_scorer.py`

- [ ] **Step 1: Write failing test**

```python
# tests/allocator/test_batch_scorer.py
import pytest
from unittest.mock import MagicMock, patch
from src.allocator.batch_scorer import BatchScorer

def test_batch_scorer_init():
    mock_llm = MagicMock()
    mock_neo4j = MagicMock()
    scorer = BatchScorer(mock_llm, mock_neo4j)
    assert scorer is not None

def test_score_single_component():
    mock_llm = MagicMock()
    mock_llm.generate.return_value = '{"H1_visibility": 1.0, "H2_space_limitation": 1.5, "H3_object_movement": 2.0, "H4_ergonomic_impact": 1.0, "H5_repetitiveness": 0.5, "S1_high_voltage": 2.0, "S2_chemical_reagent": 0.5, "S3_fire_explosion": 0.5, "S4_human_injury": 1.0, "Lh_human_loss": 1.5, "Lr_robot_loss": 1.0}'
    mock_neo4j = MagicMock()
    scorer = BatchScorer(mock_llm, mock_neo4j)
    result = scorer.score_component("Battery壳体", "EV-500")
    assert 'h_score' in result
    assert 's_score' in result
    assert 'as_score' in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/allocator/test_batch_scorer.py -v`
Expected: FAIL - No module named 'src.allocator.batch_scorer'

- [ ] **Step 3: Create `src/allocator/batch_scorer.py`**

```python
from typing import Dict, List, Optional
from src.experts import SafetyExpert, ProductionExpert, QualityExpert
from src.allocator.entropy_weight import EntropyWeightCalculator
from src.allocator.as_calculator import ASCalculator
from src.kg.client import Neo4jClient
from src.utils.llm_client import LLMClient
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
        loss_diff = final_scores['loss_diff']

        assignee = self.as_calc.determine_assignee(
            final_scores['as_score'],
            robot_cost=robot_loss,
            human_cost=human_loss
        )

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
            'loss_diff': loss_diff,
            'assignee': assignee,
        }

        if self.neo4j:
            self._update_neo4j_node(result)

        return result

    def score_all_l1_components(self, battery_model: str = '') -> List[Dict]:
        if not self.neo4j:
            raise RuntimeError("Neo4j client required for batch scoring")

        components = self.neo4j.get_all_components(battery_model=battery_model, top_k=100)
        l1_components = [c for c in components if c.get('source_type') == 'L1']

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
            'expert_A_scores': str(score_data['expert_A_scores']),
            'expert_B_scores': str(score_data['expert_B_scores']),
            'expert_C_scores': str(score_data['expert_C_scores']),
            'h_weighted_score': score_data['h_score'],
            's_weighted_score': score_data['s_score'],
            'as_score': score_data['as_score'],
            'human_loss': score_data['human_loss'],
            'robot_loss': score_data['robot_loss'],
            'loss_diff': score_data['loss_diff'],
            'assignee': score_data['assignee'],
        }

        cypher = '''
        MATCH (c:Component {name: $name})
        SET c += $props
        '''
        try:
            self.neo4j.execute_query(cypher, {'name': component_name, 'props': properties})
            logger.info(f"Updated Neo4j node for {component_name}")
        except Exception as e:
            logger.error(f"Failed to update Neo4j node {component_name}: {e}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/allocator/test_batch_scorer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/allocator/batch_scorer.py tests/allocator/test_batch_scorer.py
git commit -m "feat: add BatchScorer for three-expert scoring service"
```

---

## Task 7: Fix AS Calculator determine_assignee Logic

**Files:**
- Modify: `src/allocator/as_calculator.py:37-45`
- Modify: `tests/allocator/test_as_calculator.py`

- [ ] **Step 1: Write failing test**

```python
# tests/allocator/test_as_calculator.py - add new test
def test_determine_assignee_uses_loss_diff():
    calculator = ASCalculator()
    assert calculator.determine_assignee(0.5, robot_cost=100, human_cost=80) == 'human'
    assert calculator.determine_assignee(0.5, robot_cost=80, human_cost=100) == 'robot'
    assert calculator.determine_assignee(0.5, robot_cost=100, human_cost=100) == 'robot'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/allocator/test_as_calculator.py::test_determine_assignee_uses_loss_diff -v`
Expected: FAIL - Current logic compares cost values, not losses

- [ ] **Step 3: Fix determine_assignee in `src/allocator/as_calculator.py`**

Replace lines 37-45:
```python
def determine_assignee(self, as_score: float,
                      human_loss: float = 80.0,
                      robot_loss: float = 100.0) -> str:
    if as_score > 0.6:
        return 'robot'
    elif as_score < 0.4:
        return 'human'
    else:
        return 'human' if human_loss < robot_loss else 'robot'
```

- [ ] **Step 4: Update test_determine_assignee_cost_based to use new signature**

Update test line 29 to:
```python
assert calculator.determine_assignee(0.5, human_loss=80, robot_loss=100) == 'human'
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/allocator/test_as_calculator.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/allocator/as_calculator.py tests/allocator/test_as_calculator.py
git commit -m "fix: update determine_assignee to compare human_loss vs robot_loss"
```

---

## Task 8: Add Neo4j Update Node Method

**Files:**
- Modify: `src/kg/client.py` (add method at line ~200)

- [ ] **Step 1: Write failing test (inline with existing test pattern)**

Create `tests/kg/test_client_update.py`:
```python
import pytest
from unittest.mock import MagicMock
from src.kg.client import Neo4jClient

def test_update_component_properties():
    client = Neo4jClient('bolt://localhost:7687', 'neo4j', 'password')
    with pytest.raises(AttributeError):
        client.update_component_properties('test', {})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/kg/test_client_update.py -v`
Expected: FAIL - Method doesn't exist

- [ ] **Step 3: Add method to `src/kg/client.py` after line 210**

```python
def update_component_properties(self, component_name: str, properties: dict) -> bool:
    """Update component node properties in Neo4j."""
    cypher = '''
    MATCH (c:Component {name: $name})
    SET c += $props
    RETURN c
    '''
    try:
        result = self.execute_query(cypher, {'name': component_name, 'props': properties})
        return len(result) > 0
    except Exception as e:
        logger.error(f"Failed to update component {component_name}: {e}")
        return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/kg/test_client_update.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kg/client.py tests/kg/test_client_update.py
git commit -m "feat: add update_component_properties method to Neo4jClient"
```

---

## Task 9: Extend API Schemas with Scoring Fields

**Files:**
- Modify: `src/api/schemas.py`

- [ ] **Step 1: Write failing test**

Create `tests/api/test_schemas.py`:
```python
import pytest
from src.api.schemas import Step

def test_step_has_scoring_fields():
    step = Step(
        id=1,
        component="Battery壳体",
        action="拆卸外壳",
        tool=["螺丝刀"],
        h_score=0.65,
        s_score=0.42,
        as_score=0.535,
        human_loss=2.0,
        robot_loss=1.0,
        loss_diff=1.0,
        assignee="human"
    )
    assert step.h_score == 0.65
    assert step.assignee == "human"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_schemas.py -v`
Expected: FAIL - Fields don't exist

- [ ] **Step 3: Update Step model in `src/api/schemas.py`**

Replace the Step class (lines 11-18):
```python
class Step(BaseModel):
    id: int
    component: str
    action: str
    tool: list[str] = []
    evidence: list[str] = []
    confidence: Optional[float] = None
    safety_level: Optional[int] = None
    h_score: Optional[float] = None
    s_score: Optional[float] = None
    as_score: Optional[float] = None
    human_loss: Optional[float] = None
    robot_loss: Optional[float] = None
    loss_diff: Optional[float] = None
    assignee: Optional[str] = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/schemas.py tests/api/test_schemas.py
git commit -m "feat: extend Step schema with scoring fields"
```

---

## Task 10: Update BatchScorer to Use Neo4j Client Method

**Files:**
- Modify: `src/allocator/batch_scorer.py`

- [ ] **Step 1: Update _update_neo4j_node method to use client method**

Replace `_update_neo4j_node` method in `src/allocator/batch_scorer.py`:
```python
def _update_neo4j_node(self, score_data: Dict) -> None:
    if not self.neo4j:
        return

    component_name = score_data['component']
    properties = {
        'expert_A_scores': str(score_data['expert_A_scores']),
        'expert_B_scores': str(score_data['expert_B_scores']),
        'expert_C_scores': str(score_data['expert_C_scores']),
        'h_weighted_score': score_data['h_score'],
        's_weighted_score': score_data['s_score'],
        'as_score': score_data['as_score'],
        'human_loss': score_data['human_loss'],
        'robot_loss': score_data['robot_loss'],
        'loss_diff': score_data['loss_diff'],
        'assignee': score_data['assignee'],
    }

    try:
        self.neo4j.update_component_properties(component_name, properties)
        logger.info(f"Updated Neo4j node for {component_name}")
    except Exception as e:
        logger.error(f"Failed to update Neo4j node {component_name}: {e}")
```

- [ ] **Step 2: Commit**

```bash
git add src/allocator/batch_scorer.py
git commit -m "refactor: use Neo4jClient.update_component_properties in BatchScorer"
```

---

## Task 11: Run All Tests

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest tests/ -v --tb=short`
Expected: All tests pass

- [ ] **Step 2: Fix any failures**

Address any issues found during test run

---

## Spec Coverage Checklist

| Spec Section | Task(s) |
|--------------|---------|
| 2. Expert Roles | Tasks 1-4 |
| 3. Scoring Factors (H, S, L) | Tasks 1, 5 |
| 4. Entropy Weight Calculation | Task 5 |
| 5. Neo4j Node Properties | Tasks 6, 8, 10 |
| 6. API Return Fields | Task 9 |
| 7. Implementation Components | Tasks 1-6, 8-10 |

**Plan complete and saved to `docs/superpowers/plans/2026-04-17-three-expert-scoring-implementation-plan.md`**

---

## Execution Options

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**