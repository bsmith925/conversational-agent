import dspy
import ujson
from dspy.evaluate.metrics import answer_exact_match
from app import RAG, lm
import asyncio

# TODO: actually implement, this was just my initial notes. I need to desihn the actual eval framework. 
def main():
    dspy.settings.configure(lm=lm)

    # Load devset
    dev_set = []
    with open("devset.jsonl", "r") as f:
        for line in f:
            data = ujson.loads(line)
            # DSPy still has this awful way to create examples..reminder to self to finish that feature
            dev_set.append(
                dspy.Example(
                    question=data["question"], answer=data["response"]
                ).with_inputs("question")
            )
    print(f"Loaded {len(dev_set)} examples.")

    # What actual metrics do I care about?
    # 1. answer_exact_match: Does the model's answer exactly match the expected? strict
    # 2. answer_passage_match: Does the text of the gold answer appear in the retrieved context?
    # 3. LettuceDetect once setup to evaluate hallcinations.

    def retrieval_quality(example, pred, trace=None):
        gold_answer = example.answer
        return any(gold_answer.lower() in passage.lower() for passage in pred.context)

    evaluate = dspy.Evaluate(devset=dev_set, num_threads=1, display_progress=True)

    rag = RAG()

    def async_rag_evaluator(example, **kwargs):
        # the evaluator is sync, so async module's acall is run in the new event loop?
        return asyncio.run(
            rag.acall(question=example.question, chat_history="", **kwargs)
        )

    metrics = [
        ("Exact Match", answer_exact_match),
        ("Retrieval Quality", retrieval_quality),
    ]

    results = {}
    for metric_name, metric_func in metrics:
        score = evaluate(async_rag_evaluator, metric=metric_func)
        results[metric_name] = score

    print("\n Evaluation Results")
    for metric_name, score in results.items():
        print(f"{metric_name}: {score:.2f}%")


if __name__ == "__main__":
    main()
