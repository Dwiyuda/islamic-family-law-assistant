"""Run from the repo root with the api venv (after run_generation.py --stage generate):
HF_HUB_OFFLINE=1 api/.venv/Scripts/python eval/score_generation.py --pause 10"""

from app.evaluation.generation_report import main

if __name__ == "__main__":
    main()
