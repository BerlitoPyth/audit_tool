import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Tooltip,
} from '@mui/material';
import { Info as InfoIcon } from '@mui/icons-material';

function AnomalyTable({ anomalies, onViewDetails }) {
  const getSeverityColor = (score) => {
    if (score >= 0.8) return 'error';
    if (score >= 0.5) return 'warning';
    return 'info';
  };

  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Type</TableCell>
            <TableCell>Description</TableCell>
            <TableCell>Confiance</TableCell>
            <TableCell>Lignes</TableCell>
            <TableCell>Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {anomalies.map((anomaly) => (
            <TableRow key={anomaly.id}>
              <TableCell>{anomaly.type}</TableCell>
              <TableCell>{anomaly.description}</TableCell>
              <TableCell>
                <Chip
                  label={`${(anomaly.confidence_score * 100).toFixed(0)}%`}
                  color={getSeverityColor(anomaly.confidence_score)}
                  size="small"
                />
              </TableCell>
              <TableCell>
                {anomaly.line_numbers?.join(', ') || 'N/A'}
              </TableCell>
              <TableCell>
                <Tooltip title="Voir les détails">
                  <IconButton
                    size="small"
                    onClick={() => onViewDetails(anomaly)}
                  >
                    <InfoIcon />
                  </IconButton>
                </Tooltip>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

export default AnomalyTable;
