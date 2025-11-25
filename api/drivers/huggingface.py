from typing import Any, Dict
import json
from .base import BaseDriver, DriverResponse


class HuggingFaceDriver(BaseDriver):
    type = "huggingface"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        input_text = context.get("input", "")
        data = node.get("data") or {}

        task = data.get("task", "text-classification")
        model = data.get("model", "")

        if not model:
            return DriverResponse({
                "status": "error",
                "error": "No model specified. Please configure a Hugging Face model.",
                "output": input_text,
            })

        try:
            from transformers import pipeline  # type: ignore

            # Create pipeline based on task type
            if task == "zero-shot-classification":
                candidate_labels = data.get("candidate_labels", [])
                if not candidate_labels:
                    return DriverResponse({
                        "status": "error",
                        "error": "zero-shot-classification requires candidate_labels",
                        "output": input_text,
                    })

                # Create zero-shot classification pipeline
                pipe = pipeline("zero-shot-classification", model=model)
                result = pipe(str(input_text), candidate_labels=candidate_labels)

                # Format output as label
                top_label = result.get("labels", [None])[0] if result.get("labels") else None
                top_score = result.get("scores", [None])[0] if result.get("scores") else None

                return DriverResponse({
                    "status": "ok",
                    "output": top_label,
                    "predictions": result,
                    "label": top_label,
                    "score": top_score,
                    "model": model,
                    "task": task,
                })

            elif task == "question-answering":
                question = data.get("question", "")
                if not question:
                    return DriverResponse({
                        "status": "error",
                        "error": "question-answering requires a question parameter",
                        "output": input_text,
                    })

                # Create QA pipeline
                pipe = pipeline("question-answering", model=model)
                result = pipe(question=question, context=str(input_text))

                return DriverResponse({
                    "status": "ok",
                    "output": result.get("answer"),
                    "answer": result.get("answer"),
                    "score": result.get("score"),
                    "predictions": result,
                    "model": model,
                    "task": task,
                })

            elif task == "ner":
                # Create NER pipeline
                pipe = pipeline("ner", model=model)
                result = pipe(str(input_text))

                entities = result if isinstance(result, list) else []

                # Format output as JSON string of entities
                output = json.dumps(entities, indent=2)

                return DriverResponse({
                    "status": "ok",
                    "output": output,
                    "entities": entities,
                    "predictions": entities,
                    "model": model,
                    "task": task,
                })

            elif task == "feature-extraction":
                # Create feature extraction pipeline
                pipe = pipeline("feature-extraction", model=model)
                result = pipe(str(input_text))

                # Format output as summary of embeddings
                if isinstance(result, list) and len(result) > 0:
                    if isinstance(result[0], list) and len(result[0]) > 0:
                        dim = len(result[0][0]) if isinstance(result[0][0], list) else len(result[0])
                        output = f"Generated embeddings ({dim} dimensions)"
                    else:
                        output = "Generated embeddings"
                else:
                    output = "Generated embeddings"

                return DriverResponse({
                    "status": "ok",
                    "output": output,
                    "embeddings": result,
                    "predictions": result,
                    "model": model,
                    "task": task,
                })

            elif task in ["text-classification", "sentiment-analysis"]:
                # Create text classification pipeline
                pipe = pipeline(task, model=model)
                result = pipe(str(input_text))

                predictions = result if isinstance(result, list) else [result]
                top_prediction = predictions[0] if predictions else {}

                # Format output as label
                label = top_prediction.get("label")
                score = top_prediction.get("score")

                return DriverResponse({
                    "status": "ok",
                    "output": label,
                    "predictions": predictions,
                    "label": label,
                    "score": score,
                    "model": model,
                    "task": task,
                })

            elif task in ["summarization", "translation"]:
                # Create summarization/translation pipeline
                pipe = pipeline(task, model=model)
                result = pipe(str(input_text))

                # Extract generated text from result
                output_text = result[0].get("summary_text") if task == "summarization" else result[0].get("translation_text")

                return DriverResponse({
                    "status": "ok",
                    "output": output_text,
                    "generated_text": output_text,
                    "predictions": result,
                    "model": model,
                    "task": task,
                })

            else:
                # Generic pipeline for other tasks
                pipe = pipeline(task, model=model)
                result = pipe(str(input_text))

                # Format output as JSON
                output = json.dumps(result, indent=2)

                return DriverResponse({
                    "status": "ok",
                    "output": output,
                    "predictions": result,
                    "model": model,
                    "task": task,
                })

        except ImportError:
            return DriverResponse({
                "status": "error",
                "error": "transformers library not installed. Run: pip install transformers torch",
                "output": input_text,
            })
        except Exception as exc:
            error_msg = str(exc)

            # Check for common errors
            if "could not be found" in error_msg.lower() or "does not exist" in error_msg.lower():
                error_msg = f"Model '{model}' not found. Check the model ID on https://huggingface.co/models"
            elif "out of memory" in error_msg.lower():
                error_msg = "Out of memory. Try a smaller model or reduce batch size."

            return DriverResponse({
                "status": "error",
                "error": f"Hugging Face error: {error_msg}",
                "output": input_text,
            })
