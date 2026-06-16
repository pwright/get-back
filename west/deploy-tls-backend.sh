#!/bin/bash
# Deploy TLS-enabled getback backend to west namespace

set -e

echo "=== Deploying TLS-enabled getback backend to west namespace ==="

# Check if namespace exists
if ! kubectl get namespace west &> /dev/null; then
    echo "Error: Namespace 'west' does not exist"
    echo "Create it with: kubectl create namespace west"
    exit 1
fi

# Generate self-signed certificate
echo ""
echo "Step 1: Generating self-signed TLS certificate..."
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout /tmp/getback-tls-key.pem \
  -out /tmp/getback-tls-cert.pem \
  -days 365 \
  -subj "/CN=getback-tls" \
  2>/dev/null

echo "✓ Certificate generated"

# Create or update secret
echo ""
echo "Step 2: Creating Kubernetes secret..."
if kubectl get secret getback-tls-cert -n west &> /dev/null; then
    echo "Secret already exists, deleting and recreating..."
    kubectl delete secret getback-tls-cert -n west
fi

kubectl create secret generic getback-tls-cert \
  --from-file=cert.pem=/tmp/getback-tls-cert.pem \
  --from-file=key.pem=/tmp/getback-tls-key.pem \
  -n west

echo "✓ Secret created"

# Clean up temp files
rm /tmp/getback-tls-key.pem /tmp/getback-tls-cert.pem

# Deploy resources
echo ""
echo "Step 3: Deploying TLS backend..."
kubectl apply -f "$(dirname "$0")/deployment-tls.yaml"
kubectl apply -f "$(dirname "$0")/service-tls.yaml"

echo "✓ Deployment and service created"

# Wait for pod to be ready
echo ""
echo "Step 4: Waiting for pod to be ready..."
kubectl wait --for=condition=ready pod -l app=getback-tls -n west --timeout=60s

echo ""
echo "=== Deployment complete! ==="
echo ""
echo "TLS backend is now available at:"
echo "  - HTTPS: getback-tls.west:9091"
echo "  - TLS TCP: getback-tls.west:9092"
echo "  - Dashboard: getback-tls.west:9093"
echo ""
echo "Optional: Deploy Skupper connectors for multi-cluster:"
echo "  kubectl apply -f $(dirname "$0")/connectors-tls.yaml"
echo ""
echo "Optional: Deploy Skupper listeners for multi-cluster (in west only):"
echo "  kubectl apply -f $(dirname "$0")/listeners-tls.yaml"
echo ""
echo "Test from dashboard:"
echo "  1. Backend: getback-tls.west:9091"
echo "  2. Check 'Use HTTPS' checkbox"
echo "  3. Click 'Send HTTP Request'"
echo ""
echo "Verify pods:"
echo "  kubectl get pods -n west"
echo ""
echo "View logs:"
echo "  kubectl logs -n west -l app=getback-tls --tail=50"
echo ""
echo "Note: This deployment uses native Python SSL/TLS support (zero dependencies)"
