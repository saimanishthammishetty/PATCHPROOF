const express = require('express');
const _ = require('lodash');
const axios = require('axios');

const app = express();
app.use(express.json());

app.post('/merge', (req, res) => {
  // Vulnerable to prototype pollution via deep merge
  const target = {};
  _.zipObjectDeep(req.body.path, req.body.value);
  res.json({ status: 'ok', target });
});

app.listen(3000, () => console.log('Listening on 3000'));

