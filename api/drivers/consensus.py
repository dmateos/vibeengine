from typing import Any, Dict, List, Optional
import os
from .base import BaseDriver, DriverResponse


class ConsensusDriver(BaseDriver):
    """
    Consensus node driver that analyzes agreement among multiple responses.

    Typically used after a Join node that collects outputs from multiple agents.

    Configuration (node.data):
        method: How to judge agreement
            - 'exact': Exact string matching (case-insensitive, whitespace-trimmed)
            - 'semantic': Semantic similarity using heuristics
            - 'llm_judge': Use an LLM to judge if responses agree (default)

        threshold: Minimum agreement to reach consensus
            - 'majority': >50% must agree (default)
            - 'unanimous': 100% must agree
            - float: Custom threshold (e.g., 0.67 for 2/3)

        judge_model: Which LLM to use for llm_judge method
            - 'claude': Claude (default, uses claude_agent driver)
            - 'openai': OpenAI (uses openai_agent driver)
            - 'ollama': Ollama (uses ollama_agent driver)

        return_all: Include all individual responses in output (default: true)

    Returns:
        DriverResponse with:
            - consensus: Boolean - whether consensus was reached
            - agreement_rate: Float - percentage of responses that agree (0.0-1.0)
            - answer: The consensus answer (or most common answer)
            - analysis: Text explanation of the agreement
            - responses: All individual responses (if return_all=true)
            - disagreements: Responses that didn't match consensus
    """
    type = "consensus"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        """Execute consensus analysis on input responses."""
        data = node.get('data') or {}
        method = data.get('method', 'llm_judge')
        threshold_str = data.get('threshold', 'majority')
        judge_model = data.get('judge_model', 'claude')
        return_all = data.get('return_all', True)

        # For llm_judge method, require a connected judge node
        judge_node = None
        if method == 'llm_judge':
            judge_node = self._find_connected_judge(node, context)

            if not judge_node:
                return DriverResponse({
                    "status": "error",
                    "error": "LLM Judge method requires a judge agent node. Connect a Claude, OpenAI, or Ollama agent to the left or right handle (pink) of the Consensus node.",
                })

            # Validate that connected node is an agent type
            judge_type = judge_node.get('type', '')
            valid_agent_types = ['claude_agent', 'openai_agent', 'ollama_agent']
            if judge_type not in valid_agent_types:
                return DriverResponse({
                    "status": "error",
                    "error": f"Connected judge node must be an agent (Claude, OpenAI, or Ollama). Connected node type '{judge_type}' is not valid.",
                })

            judge_model = judge_type

        # Get input - should be a list of responses from join node
        input_val = context.get('input')

        if not isinstance(input_val, list):
            return DriverResponse({
                "status": "error",
                "error": "Consensus node requires a list of responses as input. Use a Join node before Consensus.",
            })

        if len(input_val) == 0:
            return DriverResponse({
                "status": "error",
                "error": "Consensus node received empty list of responses.",
            })

        # Convert threshold to float
        threshold = self._parse_threshold(threshold_str, len(input_val))

        # Analyze consensus based on method
        try:
            if method == 'exact':
                result = self._exact_consensus(input_val, threshold)
            elif method == 'semantic':
                result = self._semantic_consensus(input_val, threshold)
            elif method == 'llm_judge':
                result = self._llm_judge_consensus(input_val, threshold, judge_model, data, judge_node)
            else:
                return DriverResponse({
                    "status": "error",
                    "error": f"Unknown consensus method: {method}. Use 'exact', 'semantic', or 'llm_judge'.",
                })

            # Build output
            output = {
                "consensus": result['consensus'],
                "agreement_rate": result['agreement_rate'],
                "answer": result['answer'],
                "analysis": result['analysis'],
            }

            if return_all:
                output['responses'] = input_val
                output['disagreements'] = result.get('disagreements', [])

            return DriverResponse({
                "status": "ok",
                "output": output,
            })

        except Exception as e:
            return DriverResponse({
                "status": "error",
                "error": f"Consensus analysis failed: {str(e)}",
            })

    def _find_connected_judge(self, node: Dict[str, Any], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a judge agent node connected to this consensus node via 'judge-left' or 'judge-right' handle."""
        edges = context.get('_edges', [])
        nodes = context.get('_nodes', {})
        node_id = str(node.get('id'))

        # Look for edge connected to 'judge-left' or 'judge-right' target handle
        for edge in edges:
            target_handle = edge.get('targetHandle')
            if str(edge.get('target')) == node_id and target_handle in ['judge-left', 'judge-right']:
                judge_node_id = str(edge.get('source'))
                return nodes.get(judge_node_id)

        return None

    def _parse_threshold(self, threshold_str: Any, num_responses: int) -> float:
        """Parse threshold string to float."""
        if threshold_str == 'majority':
            return 0.5
        elif threshold_str == 'unanimous':
            return 1.0
        elif isinstance(threshold_str, (int, float)):
            return float(threshold_str)
        else:
            # Try to parse as float
            try:
                return float(threshold_str)
            except:
                return 0.5  # Default to majority

    def _exact_consensus(self, responses: List[Any], threshold: float) -> Dict[str, Any]:
        """Analyze consensus using exact string matching."""
        # Normalize responses (lowercase, strip whitespace)
        normalized = [str(r).lower().strip() if r is not None else '' for r in responses]

        # Count occurrences of each unique response
        counts: Dict[str, int] = {}
        response_map: Dict[str, Any] = {}  # Map normalized -> original

        for i, norm in enumerate(normalized):
            if norm not in counts:
                counts[norm] = 0
                response_map[norm] = responses[i]
            counts[norm] += 1

        # Find most common response
        max_count = max(counts.values())
        most_common = [k for k, v in counts.items() if v == max_count][0]

        agreement_rate = max_count / len(responses)
        consensus_reached = agreement_rate > threshold

        # Find disagreements
        disagreements = [responses[i] for i, norm in enumerate(normalized) if norm != most_common]

        return {
            'consensus': consensus_reached,
            'agreement_rate': agreement_rate,
            'answer': response_map[most_common],
            'analysis': f"Exact match: {max_count}/{len(responses)} responses agree ({agreement_rate:.1%}). {'Consensus reached.' if consensus_reached else 'No consensus.'}",
            'disagreements': disagreements,
        }

    def _semantic_consensus(self, responses: List[Any], threshold: float) -> Dict[str, Any]:
        """Analyze consensus using semantic similarity heuristics."""
        # Convert to strings
        str_responses = [str(r) if r is not None else '' for r in responses]

        # Normalize (lowercase, strip)
        normalized = [s.lower().strip() for s in str_responses]

        # Simple semantic matching: check if responses contain each other or share key phrases
        # Group responses that are semantically similar
        groups: List[List[int]] = []  # Each group is list of response indices

        for i, resp in enumerate(normalized):
            added_to_group = False
            for group in groups:
                # Check if this response is similar to any in the group
                if self._is_semantically_similar(resp, normalized[group[0]]):
                    group.append(i)
                    added_to_group = True
                    break

            if not added_to_group:
                # Create new group
                groups.append([i])

        # Find largest group
        largest_group = max(groups, key=len)
        max_count = len(largest_group)

        agreement_rate = max_count / len(responses)
        consensus_reached = agreement_rate > threshold

        # Get consensus answer (first response in largest group)
        consensus_answer = responses[largest_group[0]]

        # Find disagreements
        disagreements = [responses[i] for i in range(len(responses)) if i not in largest_group]

        return {
            'consensus': consensus_reached,
            'agreement_rate': agreement_rate,
            'answer': consensus_answer,
            'analysis': f"Semantic analysis: {max_count}/{len(responses)} responses are similar ({agreement_rate:.1%}). {'Consensus reached.' if consensus_reached else 'No consensus.'}",
            'disagreements': disagreements,
        }

    def _is_semantically_similar(self, text1: str, text2: str) -> bool:
        """Check if two texts are semantically similar using heuristics."""
        # Simple heuristics:
        # 1. If one contains the other (80% overlap)
        # 2. If they share significant common words

        if not text1 or not text2:
            return text1 == text2

        # Check containment
        if text1 in text2 or text2 in text1:
            return True

        # Check word overlap
        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return False

        # Remove very common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did'}
        words1 = {w for w in words1 if w not in stop_words}
        words2 = {w for w in words2 if w not in stop_words}

        if not words1 or not words2:
            return False

        # Calculate overlap
        overlap = len(words1.intersection(words2))
        union = len(words1.union(words2))

        similarity = overlap / union if union > 0 else 0

        return similarity > 0.5  # 50% word overlap

    def _llm_judge_consensus(self, responses: List[Any], threshold: float, judge_model: str, node_data: Dict[str, Any], judge_node: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Use an LLM to judge if responses agree."""
        # Build prompt for LLM
        responses_text = "\n\n".join([f"Response {i+1}:\n{resp}" for i, resp in enumerate(responses)])

        prompt = f"""Analyze the following {len(responses)} responses and determine if they agree on the same answer.

{responses_text}

Please analyze:
1. Do these responses fundamentally agree? (yes/no)
2. What percentage agree? (0-100)
3. What is the consensus answer?
4. Which response numbers agree with the consensus? (e.g., "1, 2, 3")
5. Which response numbers disagree? (e.g., "4, 5")
6. Brief explanation of agreement/disagreement

Format your response as:
CONSENSUS: [yes/no]
AGREEMENT: [percentage]
ANSWER: [consensus answer]
AGREEING: [comma-separated response numbers that agree]
DISAGREEING: [comma-separated response numbers that disagree]
ANALYSIS: [brief explanation]"""

        # Call LLM using existing agent driver
        try:
            from . import execute_node_by_type

            # Use the connected judge node's configuration
            agent_type = judge_node.get('type', 'claude_agent')

            # Make a copy and override system prompt to ensure it analyzes consensus
            judge_node_copy = dict(judge_node)
            if judge_node.get('data'):
                judge_node_copy['data'] = dict(judge_node['data'])
            else:
                judge_node_copy['data'] = {}

            # Override system prompt for consensus analysis
            judge_node_copy['data']['system_prompt'] = 'You are an expert at analyzing and comparing responses to determine consensus.'

            # Use the modified copy
            judge_node = judge_node_copy

            # Create context with the prompt as input
            judge_context = {
                'input': prompt,
            }

            # Execute the judge agent
            result = execute_node_by_type(agent_type, judge_node, judge_context)

            if result.get('status') == 'error':
                raise Exception(result.get('error', 'Judge agent failed'))

            llm_response = result.get('output', '')

            # Parse LLM response
            result = self._parse_llm_judgment(llm_response, threshold, responses)

            return result

        except Exception as e:
            # Raise error instead of silent fallback
            raise Exception(f'Judge agent failed: {str(e)}')

    def _parse_llm_judgment(self, llm_response: str, threshold: float, responses: List[Any]) -> Dict[str, Any]:
        """Parse LLM's judgment response."""
        import re
        lines = llm_response.strip().split('\n')

        consensus = False
        agreement_rate = 0.0
        answer = ""
        analysis = ""
        disagreeing_numbers = []

        for line in lines:
            line = line.strip()
            if line.startswith("CONSENSUS:"):
                consensus_text = line.split(":", 1)[1].strip().lower()
                consensus = "yes" in consensus_text or "true" in consensus_text
            elif line.startswith("AGREEMENT:"):
                agreement_text = line.split(":", 1)[1].strip()
                # Extract percentage
                match = re.search(r'(\d+(?:\.\d+)?)', agreement_text)
                if match:
                    agreement_rate = float(match.group(1)) / 100.0
            elif line.startswith("ANSWER:"):
                answer = line.split(":", 1)[1].strip()
            elif line.startswith("DISAGREEING:"):
                disagreeing_text = line.split(":", 1)[1].strip()
                # Extract numbers (e.g., "1, 3, 5" or "none")
                if disagreeing_text.lower() not in ['none', 'n/a', '']:
                    numbers = re.findall(r'\d+', disagreeing_text)
                    disagreeing_numbers = [int(n) for n in numbers]
            elif line.startswith("ANALYSIS:"):
                analysis = line.split(":", 1)[1].strip()

        # Final consensus check against threshold
        final_consensus = agreement_rate > threshold

        if not analysis:
            analysis = llm_response  # Use full response if no explicit analysis

        # Build disagreements list from LLM-identified disagreeing response numbers
        disagreements = []
        for num in disagreeing_numbers:
            # Response numbers are 1-indexed in the prompt
            idx = num - 1
            if 0 <= idx < len(responses):
                disagreements.append(responses[idx])

        return {
            'consensus': final_consensus,
            'agreement_rate': agreement_rate,
            'answer': answer if answer else llm_response,
            'analysis': analysis,
            'disagreements': disagreements,
        }
