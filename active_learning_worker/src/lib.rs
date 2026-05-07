pub mod api;
pub mod db;
pub mod ml;

use crate::ml::acquisition::AcquisitionStrategy;
use crate::db::DbPool;
use tokio::sync::mpsc;

/// Mensaje enviado al worker de re-entrenamiento.
#[derive(Debug)]
pub enum TrainingTrigger {
    Retrain(AcquisitionStrategy),
}

/// Estado compartido de la aplicacion.
#[derive(Clone)]
pub struct AppState {
    pub db: Option<DbPool>,
    pub tx: mpsc::Sender<TrainingTrigger>,
}
