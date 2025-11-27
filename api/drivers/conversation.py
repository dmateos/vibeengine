from typing import Any, Dict, List
import os
from .base import BaseDriver, DriverResponse


class ConversationDriver(BaseDriver):
    """
    Conversation node driver that manages multi-turn dialogues between agents.

    Allows multiple agents to have a back-and-forth conversation for N turns.
    Useful for debates, discussions, iterative refinement, etc.

    Configuration (node.data):
        participants: List of participant configs, each with:
            - role: Display name for this participant (e.g., "Pro", "Con", "Critic")
            - agent_type: Type of agent (e.g., "claude_agent", "openai_agent")
            - model: Optional specific model name
            - system_prompt: System prompt for this participant

        max_turns: Maximum number of conversation turns (default: 10)
            - A "turn" is one message from each participant
            - Total messages = max_turns * num_participants

        initial_prompt: Starting message/topic for the conversation

        turn_format: How to format messages passed to agents
            - 'history': Pass full conversation history (default)
            - 'last': Pass only the last message

    Returns:
        DriverResponse with:
            - transcript: Full conversation as list of messages
            - summary: Brief summary of the conversation
            - turn_count: Number of turns completed
            - participants: List of participant roles
    """
    type = "conversation"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        """Execute a multi-turn conversation between agents."""
        data = node.get('data') or {}

        # Get configuration
        participants = data.get('participants', [])
        max_turns = data.get('max_turns', 10)
        initial_prompt = data.get('initial_prompt') or context.get('input', '')
        turn_format = data.get('turn_format', 'history')

        # Validate configuration
        if not participants or len(participants) < 2:
            return DriverResponse({
                "status": "error",
                "error": "Conversation node requires at least 2 participants. Configure participants in node settings.",
            })

        if not initial_prompt:
            return DriverResponse({
                "status": "error",
                "error": "Conversation node requires an initial prompt. Provide via input or node configuration.",
            })

        # Run the conversation
        try:
            result = self._run_conversation(
                participants=participants,
                max_turns=max_turns,
                initial_prompt=initial_prompt,
                turn_format=turn_format
            )

            return DriverResponse({
                "status": "ok",
                "output": result,
            })

        except Exception as e:
            return DriverResponse({
                "status": "error",
                "error": f"Conversation failed: {str(e)}",
            })

    def _run_conversation(
        self,
        participants: List[Dict[str, Any]],
        max_turns: int,
        initial_prompt: str,
        turn_format: str
    ) -> Dict[str, Any]:
        """Run the multi-turn conversation."""
        from . import execute_node_by_type

        # Initialize conversation with the initial prompt
        transcript = [
            {
                "role": "system",
                "message": initial_prompt,
                "turn": 0,
            }
        ]

        # Run conversation for max_turns
        for turn in range(1, max_turns + 1):
            # Each participant speaks once per turn
            for participant_idx, participant in enumerate(participants):
                role = participant.get('role', f'Participant {participant_idx + 1}')
                agent_type = participant.get('agent_type', 'claude_agent')
                model = participant.get('model', '')
                system_prompt = participant.get('system_prompt', f'You are {role} in a conversation.')

                # Build input for this agent
                if turn_format == 'last' and len(transcript) > 1:
                    # Pass only the last message
                    last_msg = transcript[-1]
                    agent_input = f"{last_msg['role']}: {last_msg['message']}"
                else:
                    # Pass full conversation history
                    history_parts = []
                    for msg in transcript:
                        if msg['role'] == 'system':
                            history_parts.append(f"Topic: {msg['message']}")
                        else:
                            history_parts.append(f"{msg['role']}: {msg['message']}")
                    agent_input = "\n\n".join(history_parts)

                # Create agent node configuration
                agent_node = {
                    'id': f'conversation_{role}_{turn}_{participant_idx}',
                    'type': agent_type,
                    'data': {
                        'label': role,
                        'system_prompt': system_prompt,
                        'temperature': participant.get('temperature', 0.7),
                    }
                }

                # Add model if specified
                if model:
                    agent_node['data']['model'] = model

                # Execute the agent
                agent_context = {'input': agent_input}
                result = execute_node_by_type(agent_type, agent_node, agent_context)

                if result.get('status') == 'error':
                    # If agent fails, add error message and continue
                    message = f"[Error: {result.get('error', 'Agent failed')}]"
                else:
                    message = result.get('output', '')

                # Add to transcript
                transcript.append({
                    "role": role,
                    "message": message,
                    "turn": turn,
                    "participant_index": participant_idx,
                })

        # Build summary
        participant_roles = [p.get('role', f'Participant {i+1}') for i, p in enumerate(participants)]
        summary = f"Conversation between {', '.join(participant_roles)} for {max_turns} turns ({len(transcript) - 1} total messages)"

        return {
            "transcript": transcript,
            "summary": summary,
            "turn_count": max_turns,
            "participants": participant_roles,
            "total_messages": len(transcript) - 1,  # Exclude system message
        }
