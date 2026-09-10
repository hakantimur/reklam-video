import os
import tempfile

# Must run before any `app.core.config` import (module-level Settings()).
os.environ.setdefault("LAD_PROJECTS_ROOT", os.path.join(tempfile.gettempdir(), "lad_test_projects"))
