import config
import gerrit
import log
import logging
import time


logger = log.get_logger()


def send_upstream(yaml_file, event):
    """
    Creates a gerrit.commentAdded event. Lets the commentAdded object
    decide whether or not sending a proposed change to upstream is necessary.

    @param yaml_file - String yaml file name
    @param event - String event that should contain json

    """
    try:
        _config = config.load_config(yaml_file)

        start = time.time()
        logger.info("send upstream starting...")

        downstream = gerrit.Remote(_config['gerrit'])
        upstream = gerrit.Remote(_config['upstream'])

        event_obj = gerrit.CommentAdded(event)
        event_obj.send_upstream(downstream, upstream, _config)

        duration = time.time() - start
        msg = "send upstream run finished in %s seconds." % duration
        logger.info(msg)
        print msg
    except Exception as e:
        logging.exception("Error occurred:")
        raise e
