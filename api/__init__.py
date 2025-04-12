from api.route import router
from api.debug import debug
from api.option import option

router.include_router(debug)
router.include_router(option)
