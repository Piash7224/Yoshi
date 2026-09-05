const mongoose = require('mongoose');

const projectSchema = new mongoose.Schema({
  name: { type: String, required: true, trim: true },
  path: { type: String, required: true, unique: true },
  profile: { type: mongoose.Schema.Types.Mixed, default: {} },
  readiness: { type: mongoose.Schema.Types.Mixed, default: {} },
  documentation: { type: mongoose.Schema.Types.Mixed, default: {} },
}, { timestamps: true });

const eventSchema = new mongoose.Schema({
  project: { type: mongoose.Schema.Types.ObjectId, ref: 'Project', required: true },
  type: { type: String, required: true },
  commitHash: String,
  raw: { type: mongoose.Schema.Types.Mixed, default: {} },
  analysis: { type: mongoose.Schema.Types.Mixed, default: {} },
}, { timestamps: true });

module.exports = {
  Project: mongoose.model('Project', projectSchema),
  ProjectEvent: mongoose.model('ProjectEvent', eventSchema),
};
