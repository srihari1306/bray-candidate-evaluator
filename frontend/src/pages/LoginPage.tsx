/**
 * Login page with branded hero and animated background.
 */
import { Box, Button, Typography, Paper, useTheme } from '@mui/material';
import { Login as LoginIcon, DocumentScanner as LogoIcon } from '@mui/icons-material';

interface LoginPageProps {
  onLogin: () => void;
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const theme = useTheme();

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 40%, #312e81 70%, #0f172a 100%)',
        backgroundSize: '400% 400%',
        animation: 'gradientShift 15s ease infinite',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Floating orbs */}
      {[...Array(5)].map((_, i) => (
        <Box
          key={i}
          sx={{
            position: 'absolute',
            width: 200 + i * 100,
            height: 200 + i * 100,
            borderRadius: '50%',
            background: `radial-gradient(circle, ${
              ['#667eea22', '#764ba222', '#14b8a622', '#818cf822', '#2dd4bf22'][i]
            }, transparent)`,
            top: `${10 + i * 15}%`,
            left: `${5 + i * 20}%`,
            animation: `pulse ${3 + i}s ease-in-out infinite`,
            animationDelay: `${i * 0.5}s`,
          }}
        />
      ))}

      <Paper
        elevation={0}
        className="animate-slide-up"
        sx={{
          p: 6,
          maxWidth: 440,
          width: '90%',
          textAlign: 'center',
          borderRadius: '24px',
          background: 'rgba(30, 41, 59, 0.85)',
          backdropFilter: 'blur(30px)',
          border: '1px solid rgba(255,255,255,0.1)',
          position: 'relative',
          zIndex: 1,
        }}
      >
        {/* Logo */}
        <Box
          sx={{
            width: 72,
            height: 72,
            borderRadius: '20px',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            mx: 'auto',
            mb: 3,
            boxShadow: '0 8px 32px rgba(102, 126, 234, 0.4)',
          }}
        >
          <LogoIcon sx={{ color: '#fff', fontSize: 36 }} />
        </Box>

        <Typography
          variant="h4"
          fontWeight={800}
          sx={{
            mb: 1,
            background: 'linear-gradient(135deg, #fff 0%, #a5b4fc 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          Candidate Evaluator
        </Typography>

        <Typography variant="body1" sx={{ color: '#94a3b8', mb: 1 }}>
          AI-Powered Resume Scanner
        </Typography>

        <Typography variant="body2" sx={{ color: '#64748b', mb: 4, px: 2 }}>
          Evaluate candidates against job descriptions using Azure AI
          with semantic scoring and intelligent skill matching.
        </Typography>

        <Button
          variant="contained"
          size="large"
          startIcon={<LoginIcon />}
          onClick={onLogin}
          fullWidth
          sx={{
            py: 1.5,
            fontSize: '1rem',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            boxShadow: '0 4px 20px rgba(102, 126, 234, 0.4)',
            '&:hover': {
              background: 'linear-gradient(135deg, #5a6fd6 0%, #6a4296 100%)',
              boxShadow: '0 6px 24px rgba(102, 126, 234, 0.5)',
            },
          }}
        >
          Sign in with Azure AD
        </Button>

        <Typography variant="caption" sx={{ color: '#475569', mt: 3, display: 'block' }}>
          Secured by Microsoft Entra ID
        </Typography>
      </Paper>
    </Box>
  );
}
