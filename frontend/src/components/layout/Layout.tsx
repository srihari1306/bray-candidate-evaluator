/**
 * Main application layout with sidebar navigation and top app bar.
 */
import { useState, type ReactNode } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  AppBar, Box, Toolbar, Typography, IconButton, Drawer,
  List, ListItem, ListItemButton, ListItemIcon, ListItemText,
  Avatar, Tooltip, Divider, useTheme, Badge, Chip,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Science as EvalIcon,
  History as HistoryIcon,
  Brightness4 as DarkIcon,
  Brightness7 as LightIcon,
  Menu as MenuIcon,
  Logout as LogoutIcon,
  DocumentScanner as LogoIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
} from '@mui/icons-material';
import { useThemeContext } from '../../App';

const DRAWER_WIDTH = 260;
const COLLAPSED_WIDTH = 88;

const navItems = [
  { label: 'Dashboard', icon: <DashboardIcon />, path: '/' },
  { label: 'New Evaluation', icon: <EvalIcon />, path: '/evaluate' },
  { label: 'History', icon: <HistoryIcon />, path: '/history' },
];

interface LayoutProps {
  children: ReactNode;
  onLogout: () => void;
}

export default function Layout({ children, onLogout }: LayoutProps) {
  const theme = useTheme();
  const { isDark, toggleTheme } = useThemeContext();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isRetracted, setIsRetracted] = useState(false);
  
  const currentWidth = isRetracted ? COLLAPSED_WIDTH : DRAWER_WIDTH;

  const drawerContent = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflowX: 'hidden' }}>
      {/* Logo & Toggle */}
      <Box
        sx={{
          p: isRetracted ? 2 : 3,
          display: 'flex',
          alignItems: 'center',
          justifyContent: isRetracted ? 'center' : 'space-between',
          gap: 1.5,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, overflow: 'hidden' }}>
          <Box
            sx={{
              minWidth: 40,
              width: 40,
              height: 40,
              borderRadius: '12px',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <LogoIcon sx={{ color: '#fff', fontSize: 22 }} />
          </Box>
          {!isRetracted && (
            <Box>
              <Typography variant="subtitle1" fontWeight={700} lineHeight={1.2} noWrap>
                Candidate
              </Typography>
              <Typography variant="caption" color="text.secondary" fontWeight={500} noWrap>
                Evaluator
              </Typography>
            </Box>
          )}
        </Box>
        {!isRetracted && (
          <IconButton onClick={() => setIsRetracted(true)} size="small" sx={{ ml: 'auto' }}>
            <ChevronLeftIcon />
          </IconButton>
        )}
      </Box>

      {isRetracted && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mb: 1 }}>
          <IconButton onClick={() => setIsRetracted(false)} size="small">
            <ChevronRightIcon />
          </IconButton>
        </Box>
      )}

      <Divider sx={{ mx: isRetracted ? 1 : 2 }} />

      {/* Navigation */}
      <List sx={{ px: isRetracted ? 1 : 1.5, py: 2, flexGrow: 1 }}>
        {navItems.map((item) => {
          const active = location.pathname === item.path;
          const button = (
            <ListItemButton
              onClick={() => {
                navigate(item.path);
                setMobileOpen(false);
              }}
              sx={{
                borderRadius: '10px',
                py: 1.2,
                px: isRetracted ? 1 : 2,
                justifyContent: isRetracted ? 'center' : 'flex-start',
                ...(active && {
                  background: `linear-gradient(135deg, ${theme.palette.primary.main}22, ${theme.palette.primary.main}11)`,
                  border: `1px solid ${theme.palette.primary.main}33`,
                  '& .MuiListItemIcon-root': {
                    color: theme.palette.primary.main,
                  },
                  '& .MuiListItemText-primary': {
                    color: theme.palette.primary.main,
                    fontWeight: 600,
                  },
                }),
                '&:hover': {
                  background: active ? undefined : theme.palette.action.hover,
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: isRetracted ? 0 : 40, mr: isRetracted ? 0 : 'auto', justifyContent: 'center' }}>
                {item.icon}
              </ListItemIcon>
              {!isRetracted && <ListItemText primary={item.label} />}
              {active && !isRetracted && (
                <Box
                  sx={{
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    bgcolor: theme.palette.primary.main,
                  }}
                />
              )}
            </ListItemButton>
          );

          return (
            <ListItem key={item.path} disablePadding sx={{ mb: 0.5, display: 'block' }}>
              {isRetracted ? (
                <Tooltip title={item.label} placement="right">
                  {button}
                </Tooltip>
              ) : (
                button
              )}
            </ListItem>
          );
        })}
      </List>

      {/* Bottom section */}
      <Box sx={{ p: isRetracted ? 1 : 2 }}>
        {!isRetracted && (
          <Chip
            label="Mock Mode"
            size="small"
            color="secondary"
            variant="outlined"
            sx={{ mb: 2, width: '100%' }}
          />
        )}
        <Box
          sx={{
            p: isRetracted ? 1 : 2,
            borderRadius: '12px',
            bgcolor: theme.palette.action.hover,
            display: 'flex',
            alignItems: 'center',
            justifyContent: isRetracted ? 'center' : 'flex-start',
            gap: 1.5,
          }}
        >
          {isRetracted ? (
            <Tooltip title="Logout" placement="right">
              <IconButton onClick={onLogout} size="small" sx={{ p: 0 }}>
                <Avatar
                  sx={{
                    width: 36,
                    height: 36,
                    bgcolor: theme.palette.primary.main,
                    fontSize: '0.85rem',
                  }}
                >
                  DU
                </Avatar>
              </IconButton>
            </Tooltip>
          ) : (
            <>
              <Avatar
                sx={{
                  width: 36,
                  height: 36,
                  bgcolor: theme.palette.primary.main,
                  fontSize: '0.85rem',
                }}
              >
                DU
              </Avatar>
              <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                <Typography variant="body2" fontWeight={600} noWrap>
                  Dev User
                </Typography>
                <Typography variant="caption" color="text.secondary" noWrap>
                  Recruiter
                </Typography>
              </Box>
              <Tooltip title="Logout">
                <IconButton size="small" onClick={onLogout}>
                  <LogoutIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </>
          )}
        </Box>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar - Desktop */}
      <Drawer
        variant="permanent"
        sx={{
          display: { xs: 'none', md: 'block' },
          width: currentWidth,
          transition: theme.transitions.create('width', {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.enteringScreen,
          }),
          '& .MuiDrawer-paper': {
            width: currentWidth,
            transition: theme.transitions.create('width', {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            }),
            overflowX: 'hidden',
            borderRight: `1px solid ${theme.palette.divider}`,
            bgcolor: theme.palette.background.paper,
          },
        }}
        open
      >
        {drawerContent}
      </Drawer>

      {/* Sidebar - Mobile */}
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
        sx={{
          display: { xs: 'block', md: 'none' },
          '& .MuiDrawer-paper': { width: DRAWER_WIDTH },
        }}
      >
        {drawerContent}
      </Drawer>

      {/* Main content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          minHeight: '100vh',
          bgcolor: theme.palette.background.default,
        }}
      >
        {/* Top bar */}
        <AppBar
          position="sticky"
          elevation={0}
          sx={{
            bgcolor: theme.palette.background.paper,
            borderBottom: `1px solid ${theme.palette.divider}`,
          }}
        >
          <Toolbar>
            <IconButton
              sx={{ display: { md: 'none' }, mr: 1 }}
              onClick={() => setMobileOpen(true)}
            >
              <MenuIcon />
            </IconButton>
            <Box sx={{ flexGrow: 1 }} />
            <Tooltip title={isDark ? 'Light Mode' : 'Dark Mode'}>
              <IconButton onClick={toggleTheme} sx={{ mr: 1 }}>
                {isDark ? <LightIcon /> : <DarkIcon />}
              </IconButton>
            </Tooltip>
          </Toolbar>
        </AppBar>

        {/* Page content */}
        <Box sx={{ p: { xs: 2, md: 3 } }}>{children}</Box>
      </Box>
    </Box>
  );
}
