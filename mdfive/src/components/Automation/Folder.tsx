import React from 'react';
import { Card, Col, Container, Row } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import SideBar from '../SideBar';

const FolderTile: React.FC<{ title: string; to: string; emoji: string }> = ({ title, to, emoji }) => (
  <Col md={4} className="mb-4">
    <Link to={to} style={{ textDecoration: 'none' }}>
      <Card className="h-100 shadow-sm">
        <Card.Body className="d-flex align-items-center justify-content-center" style={{ minHeight: 160 }}>
          <div className="text-center">
            <div style={{ fontSize: 48 }}>{emoji}</div>
            <div className="mt-3 fw-semibold" style={{ fontSize: 18 }}>{title}</div>
          </div>
        </Card.Body>
      </Card>
    </Link>
  </Col>
);

const AutomationFolder: React.FC = () => {
  return (
    <Row>
      <Col md={2}>
        <SideBar />
      </Col>
      <Col>
        <Container fluid className="py-4">
          <h4 className="mb-4">Automation</h4>
          <Row>
            <FolderTile title="Sign In" to="/automation/signin" emoji="🔐" />
            <FolderTile title="Sign Up" to="/automation/signup" emoji="📝" />
            <FolderTile title="Forgot Password" to="/automation/forgot" emoji="🔄" />
          </Row>
        </Container>
      </Col>
    </Row>
  );
};

export default AutomationFolder;


