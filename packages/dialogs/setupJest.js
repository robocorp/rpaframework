require('jest-fetch-mock').enableMocks();

process.on('unhandledRejection', reason => {
  console.error(reason);
});
