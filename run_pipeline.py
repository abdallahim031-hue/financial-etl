import logging
import time

import extract, transform, load

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s : %(message)s")
log = logging.getLogger("pipeline")


def with_retry(fn, tries=3, wait=30):
    for i in range(1, tries + 1):
        try:
            return fn()
        except Exception as e:
            log.warning("Échec (essai %d/%d) : %s", i, tries, e)
            if i == tries:
                raise
            time.sleep(wait)


def main():
    log.info("=== Début du pipeline ===")
    with_retry(extract.run)
    enriched, company = transform.run()
    load.run(enriched, company)
    log.info("=== Pipeline terminé ===")


if __name__ == "__main__":
    main()
