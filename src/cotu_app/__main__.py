"""python -m cotu_app opens the main desktop application."""

import multiprocessing
import sys
from .app.desktop import main, use_project_environment

if __name__ == "__main__":
    use_project_environment()
    multiprocessing.freeze_support()
    sys.exit(main())
