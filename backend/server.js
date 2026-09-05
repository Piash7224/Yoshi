const express = require('express');
const cors = require('cors');
const mongoose = require('mongoose');
require('dotenv').config();
const { aiPost } = require('./aiClient');
const { Project, ProjectEvent } = require('./models');

const app = express();
app.use(cors());
app.use(express.json({ limit: '2mb' }));

app.get('/api/health', (_req, res) => res.json({ status: 'ok', database: mongoose.connection.readyState === 1 ? 'connected' : 'disconnected' }));
app.get('/api/projects', async (_req, res, next) => { try { res.json(await Project.find().sort({ updatedAt: -1 }).lean()); } catch (e) { next(e); } });

app.post('/api/projects', async (req, res, next) => {
  try {
    const info = await aiPost('/repository/info', { path: req.body.path });
    const project = await Project.findOneAndUpdate(
      { path: info.path }, { name: req.body.name || info.name, path: info.path },
      { upsert: true, new: true, runValidators: true },
    );
    res.status(201).json(project);
  } catch (e) { next(e); }
});

app.post('/api/projects/:id/scan', async (req, res, next) => {
  try {
    const project = await Project.findById(req.params.id);
    if (!project) return res.status(404).json({ error: 'Project not found' });
    const [profile, readiness, documentation, memory, commits] = await Promise.all([
      aiPost('/repository/profile', { path: project.path }), aiPost('/repository/readiness', { path: project.path }),
      aiPost('/repository/documentation', { path: project.path }), aiPost('/memory/index', { path: project.path }),
      aiPost('/repository/commits', { path: project.path, limit: 20 }),
    ]);
    Object.assign(project, { profile, readiness, documentation });
    await project.save();
    res.json({ project, memory, commits });
  } catch (e) { next(e); }
});

app.post('/api/projects/:id/analyze', async (req, res, next) => {
  try {
    const project = await Project.findById(req.params.id);
    if (!project) return res.status(404).json({ error: 'Project not found' });
    const raw = await aiPost('/repository/commit', { path: project.path, commit: req.body.commit || 'HEAD' });
    const analysis = await aiPost('/analyze-commit', { diff: raw.diff, commit_message: raw.message, stat_summary: raw.stat_summary, project_context: raw.project_context || '' });
    const event = await ProjectEvent.findOneAndUpdate(
      { project: project._id, commitHash: raw.hash }, { type: 'COMMIT_ANALYZED', raw, analysis }, { upsert: true, new: true },
    );
    res.json(event);
  } catch (e) { next(e); }
});

app.get('/api/projects/:id/events', async (req, res, next) => {
  try { res.json(await ProjectEvent.find({ project: req.params.id }).sort({ createdAt: -1 }).lean()); } catch (e) { next(e); }
});

app.post('/api/projects/:id/query', async (req, res, next) => {
  try {
    const project = await Project.findById(req.params.id);
    if (!project) return res.status(404).json({ error: 'Project not found' });
    const answer = await aiPost('/memory/query', { path: project.path, question: req.body.question, limit: req.body.limit || 5 });
    const sources = await aiPost('/memory/retrieve', { path: project.path, question: req.body.question, limit: req.body.limit || 5 });
    res.json({ question: req.body.question, ...answer, context: sources });
  } catch (e) { next(e); }
});

app.post('/api/projects/:id/agent/plan', async (req, res, next) => {
  try {
    const project = await Project.findById(req.params.id);
    if (!project) return res.status(404).json({ error: 'Project not found' });
    res.json(await aiPost('/agent/plan', { path: project.path, question: req.body.goal, limit: 5 }));
  } catch (e) { next(e); }
});

app.use((error, _req, res, _next) => { console.error(error.message); res.status(error.status || 500).json({ error: error.message || 'Internal server error' }); });

async function start() {
  if (!process.env.MONGODB_URI) throw new Error('MONGODB_URI is required');
  await mongoose.connect(process.env.MONGODB_URI, { serverSelectionTimeoutMS: 5000 });
  return app.listen(process.env.PORT || 5000, () => console.log('Yoshi backend listening'));
}

if (require.main === module) start().catch((error) => { console.error(error.message); process.exitCode = 1; });
module.exports = { app, start };
