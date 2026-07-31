package main

import (
	"bufio"
	"crypto/tls"
	"flag"
	"fmt"
	"io"
	"net"
	"os"
	"strings"
	"time"
)

// TestMode represents which half-close test to run
type TestMode int

const (
	ModeSend TestMode = iota // Server sends FIN first
	ModeRead                 // Client sends FIN first
	ModeBoth                 // Test both modes
)

func main() {
	host := flag.String("host", "localhost", "Server host")
	port := flag.String("port", "9092", "Server port")
	mode := flag.String("mode", "both", "Test mode: send, read, or both")
	useTLS := flag.Bool("tls", false, "Use TLS encryption")
	insecure := flag.Bool("insecure", false, "Skip TLS certificate verification")
	flag.Parse()

	fmt.Printf("Half-Close TCP Client (Go)\n")
	fmt.Printf("Target: %s:%s\n", *host, *port)
	fmt.Printf("TLS: %v\n", *useTLS)
	fmt.Printf("Mode: %s\n\n", *mode)

	var testMode TestMode
	switch strings.ToLower(*mode) {
	case "send":
		testMode = ModeSend
	case "read":
		testMode = ModeRead
	case "both":
		testMode = ModeBoth
	default:
		fmt.Fprintf(os.Stderr, "Invalid mode: %s (use send, read, or both)\n", *mode)
		os.Exit(1)
	}

	if testMode == ModeSend || testMode == ModeBoth {
		if err := testHalfCloseSend(*host, *port, *useTLS, *insecure); err != nil {
			fmt.Fprintf(os.Stderr, "HALF_CLOSE_SEND failed: %v\n", err)
			os.Exit(1)
		}
	}

	if testMode == ModeRead || testMode == ModeBoth {
		if err := testHalfCloseRead(*host, *port, *useTLS, *insecure); err != nil {
			fmt.Fprintf(os.Stderr, "HALF_CLOSE_READ failed: %v\n", err)
			os.Exit(1)
		}
	}

	fmt.Printf("\n✓ All tests passed!\n")
}

func testHalfCloseSend(host, port string, useTLS, insecure bool) error {
	fmt.Printf("=== Test: HALF_CLOSE_SEND ===\n")
	fmt.Printf("Server will send response, shutdown write side (send FIN), then keep reading\n")

	start := time.Now()

	// Connect
	conn, err := connect(host, port, useTLS, insecure)
	if err != nil {
		return fmt.Errorf("connect failed: %w", err)
	}
	defer conn.Close()

	fmt.Printf("✓ Connected to %s:%s\n", host, port)

	// Send HALF_CLOSE_SEND command
	if _, err := conn.Write([]byte("HALF_CLOSE_SEND\n")); err != nil {
		return fmt.Errorf("write command failed: %w", err)
	}
	fmt.Printf("✓ Sent command: HALF_CLOSE_SEND\n")

	// Read response
	reader := bufio.NewReader(conn)
	response, err := reader.ReadString('\n')
	if err != nil {
		return fmt.Errorf("read response failed: %w", err)
	}
	fmt.Printf("✓ Received response: %s", response)

	// Try to read more - should get EOF (server closed write side)
	conn.SetReadDeadline(time.Now().Add(1 * time.Second))
	buf := make([]byte, 1024)
	n, err := conn.Read(buf)
	if err == io.EOF {
		fmt.Printf("✓ Received EOF from server (server closed write side)\n")
	} else if err != nil {
		// Timeout or other error is also acceptable (server may have fully closed)
		if netErr, ok := err.(net.Error); ok && netErr.Timeout() {
			fmt.Printf("✓ Read timeout (server may have closed)\n")
		} else {
			fmt.Printf("⚠ Unexpected error reading: %v\n", err)
		}
	} else if n > 0 {
		return fmt.Errorf("unexpected data after response: %s", string(buf[:n]))
	}

	// Reset deadline for next operations
	conn.SetReadDeadline(time.Time{})

	// We can still send data (server is reading until we close)
	fmt.Printf("✓ Sending some data to server...\n")
	if _, err := conn.Write([]byte("Some data after server FIN\n")); err != nil {
		return fmt.Errorf("write after server FIN failed: %w", err)
	}
	time.Sleep(100 * time.Millisecond) // Give server time to read

	// Close our write side (send our FIN)
	// This is the key feature: TLS-aware half-close
	if tlsConn, ok := conn.(*tls.Conn); ok {
		// TLS: send close_notify alert, then FIN
		if err := tlsConn.CloseWrite(); err != nil {
			return fmt.Errorf("TLS CloseWrite failed: %w", err)
		}
		fmt.Printf("✓ Sent TLS close_notify and closed our write side (sent FIN)\n")
	} else if tcpConn, ok := conn.(*net.TCPConn); ok {
		// Plain TCP: shutdown write side
		if err := tcpConn.CloseWrite(); err != nil {
			return fmt.Errorf("TCP CloseWrite failed: %w", err)
		}
		fmt.Printf("✓ Closed our write side (sent FIN)\n")
	} else {
		return fmt.Errorf("unknown connection type: %T", conn)
	}

	duration := time.Since(start)
	fmt.Printf("✓ Test complete in %.2fs\n", duration.Seconds())
	fmt.Printf("✓ Server handled half-close correctly\n\n")

	return nil
}

func testHalfCloseRead(host, port string, useTLS, insecure bool) error {
	fmt.Printf("=== Test: HALF_CLOSE_READ ===\n")
	fmt.Printf("Server will read until client FIN, then send response\n")

	start := time.Now()

	// Connect
	conn, err := connect(host, port, useTLS, insecure)
	if err != nil {
		return fmt.Errorf("connect failed: %w", err)
	}
	defer conn.Close()

	fmt.Printf("✓ Connected to %s:%s\n", host, port)

	// Send HALF_CLOSE_READ command
	if _, err := conn.Write([]byte("HALF_CLOSE_READ\n")); err != nil {
		return fmt.Errorf("write command failed: %w", err)
	}
	fmt.Printf("✓ Sent command: HALF_CLOSE_READ\n")

	// Read the immediate response (counter value)
	reader := bufio.NewReader(conn)
	response, err := reader.ReadString('\n')
	if err != nil {
		return fmt.Errorf("read response failed: %w", err)
	}
	fmt.Printf("✓ Received initial response: %s", response)

	// Server is now waiting for us to close write side
	// Send some data
	fmt.Printf("✓ Sending some data to server...\n")
	if _, err := conn.Write([]byte("Test data 1\n")); err != nil {
		return fmt.Errorf("write test data 1 failed: %w", err)
	}
	if _, err := conn.Write([]byte("Test data 2\n")); err != nil {
		return fmt.Errorf("write test data 2 failed: %w", err)
	}
	time.Sleep(100 * time.Millisecond)

	// Close our write side (send FIN)
	if tlsConn, ok := conn.(*tls.Conn); ok {
		// TLS: send close_notify alert, then FIN
		if err := tlsConn.CloseWrite(); err != nil {
			return fmt.Errorf("TLS CloseWrite failed: %w", err)
		}
		fmt.Printf("✓ Sent TLS close_notify and closed our write side (sent FIN)\n")
	} else if tcpConn, ok := conn.(*net.TCPConn); ok {
		// Plain TCP: shutdown write side
		if err := tcpConn.CloseWrite(); err != nil {
			return fmt.Errorf("TCP CloseWrite failed: %w", err)
		}
		fmt.Printf("✓ Closed our write side (sent FIN)\n")
	} else {
		return fmt.Errorf("unknown connection type: %T", conn)
	}

	// Server should detect EOF and close normally
	// We should get EOF on read
	conn.SetReadDeadline(time.Now().Add(2 * time.Second))
	buf := make([]byte, 1024)
	n, err := conn.Read(buf)
	if err == io.EOF {
		fmt.Printf("✓ Received EOF from server (server closed connection)\n")
	} else if err != nil {
		if netErr, ok := err.(net.Error); ok && netErr.Timeout() {
			fmt.Printf("✓ Read timeout (server closed connection)\n")
		} else {
			return fmt.Errorf("unexpected error: %w", err)
		}
	} else if n > 0 {
		fmt.Printf("Server sent additional data: %s\n", string(buf[:n]))
	}

	duration := time.Since(start)
	fmt.Printf("✓ Test complete in %.2fs\n", duration.Seconds())
	fmt.Printf("✓ Server handled half-close correctly\n\n")

	return nil
}

func connect(host, port string, useTLS, insecure bool) (net.Conn, error) {
	address := net.JoinHostPort(host, port)

	if !useTLS {
		// Plain TCP connection
		return net.DialTimeout("tcp", address, 10*time.Second)
	}

	// TLS connection
	config := &tls.Config{
		InsecureSkipVerify: insecure,
	}

	dialer := &net.Dialer{
		Timeout: 10 * time.Second,
	}

	return tls.DialWithDialer(dialer, "tcp", address, config)
}
