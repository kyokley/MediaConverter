import requests
from settings import (WAITER_USERNAME,
                      WAITER_PASSWORD,
                      MEDIAVIEWER_FILE_URL,
                      MEDIAVIEWER_UNSTREAMABLE_FILE_URL,
                      MEDIAVIEWER_CERT,
                      )
from convert import makeFileStreamable, reencodeFilesInDirectory
class LegacyFilesClient(object):
    def putData(self, pk, newFilename):
        data = {'filename': newFilename,
                'streamable': True,
                }
        requests.put(MEDIAVIEWER_FILE_URL + '%s/' % pk,
                     data=data,
                     auth=(WAITER_USERNAME, WAITER_PASSWORD),
                     verify=MEDIAVIEWER_CERT,
                     )

    def getUnstreamableFiles(self):
        data = {'next': MEDIAVIEWER_UNSTREAMABLE_FILE_URL}
        while data['next']:
            request = requests.get(data['next'], verify=False)
            data = request.json()

            if data['results']:
                yield data['results']
        else:
            raise StopIteration

    def run(self, iterations=1, dryRun=False):
        fileGen = self.getUnstreamableFiles()
        for i in xrange(iterations):
            try:
                fileList = fileGen.next()
            except StopIteration:
                break

            for file in fileList:
                if file['ismovie']:
                    errors = reencodeFilesInDirectory(file['filename'], dryRun=dryRun)
                    if errors:
                        log.error("Something bad happened. Attempting to continue")
                        for error in errors:
                            log.error(errors)
                    else:
                        if not dryRun:
                            self.putData(file['pk'], file['filename'])
                else:
                    # Running update on a tv show
                    fullPath = os.path.join(file['localpath'], file['filename'])
                    try:
                        fullPath = makeFileStreamable(fullPath,
                                                      appendSuffix=True,
                                                      removeOriginal=True,
                                                      dryRun=dryRun)
                    except Exception, e:
                        print e
                        log.error(e)
                        log.error("Something bad happened. Attempting to continue")

                    if os.path.exists(fullPath) and not dryRun:
                        #TODO: Make call to update filename
                        newFilename = os.path.basename(fullPath)
                        if newFilename != file['filename']:
                            self.putData(file['pk'], os.path.basename(fullPath))

