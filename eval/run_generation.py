"""Run from the repo root with the api venv:
api/.venv/Scripts/python eval/run_generation.py --stage hits --device cpu --threads 8
api/.venv/Scripts/python eval/run_generation.py --stage generate"""

from app.evaluation.generation import main

if __name__ == "__main__":
    main()
