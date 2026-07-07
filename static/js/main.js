import { setupFileUpload } from './modules/fileUpload.js';
import { setupDragDrop } from './modules/dragDrop.js';
import { setupNavigation } from './modules/navigation.js';
import { setupMediaSelection } from './modules/mediaSelection.js';
import { setupTranslationProgress } from './modules/translationProgress.js';
import { setupReviewCorrections } from './modules/reviewCorrections.js';

// Inicializa todos os módulos
document.addEventListener('DOMContentLoaded', () => {
  setupFileUpload();
  setupDragDrop();
  setupNavigation();
  setupMediaSelection();
  setupTranslationProgress();
  setupReviewCorrections();
});