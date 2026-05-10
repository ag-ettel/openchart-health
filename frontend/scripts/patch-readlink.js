// Workaround for Windows 11 build 26200+ where fs.readlink returns EISDIR
// on regular (non-symlink) files instead of EINVAL. Webpack handles EINVAL
// correctly (means "not a symlink") but EISDIR crashes the build.
// This patch converts EISDIR → EINVAL for readlink calls.
const fs = require('fs');

function makeEinval(originalErr) {
  const err = new Error('EINVAL: invalid argument, readlink \'' + originalErr.path + '\'');
  err.code = 'EINVAL';
  err.errno = -22;
  err.syscall = 'readlink';
  err.path = originalErr.path;
  return err;
}

const origReadlinkSync = fs.readlinkSync;
fs.readlinkSync = function patchedReadlinkSync(p, options) {
  try {
    return origReadlinkSync.call(fs, p, options);
  } catch (err) {
    if (err.code === 'EISDIR') throw makeEinval(err);
    throw err;
  }
};

const origReadlink = fs.readlink;
fs.readlink = function patchedReadlink(p, options, callback) {
  if (typeof options === 'function') {
    callback = options;
    options = undefined;
  }
  origReadlink.call(fs, p, options, (err, result) => {
    if (err && err.code === 'EISDIR') {
      callback(makeEinval(err));
    } else {
      callback(err, result);
    }
  });
};

const origPromises = fs.promises.readlink;
fs.promises.readlink = async function patchedReadlinkPromise(p, options) {
  try {
    return await origPromises.call(fs.promises, p, options);
  } catch (err) {
    if (err.code === 'EISDIR') throw makeEinval(err);
    throw err;
  }
};
