import React from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Container, Box, Typography, AppBar, Toolbar } from '@mui/material';
import ClientIntakeForm from './components/ClientIntakeForm';

// Create Material-UI theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#2c5aa0',
      light: '#5a7bb8',
      dark: '#1e3d6f',
    },
    secondary: {
      main: '#f50057',
    },
    background: {
      default: '#f5f5f5',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h4: {
      fontWeight: 600,
    },
    h6: {
      fontWeight: 500,
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: 8,
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 12,
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 8,
          },
        },
      },
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ flexGrow: 1 }}>
        <AppBar position="static" elevation={0}>
          <Toolbar>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              Sumano Tech - Operations Management System
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.8 }}>
              Client Intake Portal
            </Typography>
          </Toolbar>
        </AppBar>
        
        <Container maxWidth={false} sx={{ py: 4 }}>
          <ClientIntakeForm />
        </Container>
        
        <Box 
          component="footer" 
          sx={{ 
            bgcolor: 'background.paper', 
            py: 3, 
            mt: 4,
            borderTop: '1px solid',
            borderColor: 'divider'
          }}
        >
          <Container maxWidth="lg">
            <Typography variant="body2" color="text.secondary" align="center">
              © 2024 Sumano Tech. All rights reserved.
            </Typography>
            <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 1 }}>
              For support, contact: support@sumano.com
            </Typography>
          </Container>
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App;
