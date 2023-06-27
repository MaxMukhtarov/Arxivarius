import cv2
def scan_qr_code():
    camera = cv2.VideoCapture(0)

    while True:
        # Read a frame from the camera
        ret, frame = camera.read()

        # Display the frame in a window
        cv2.imshow('Camera', frame)

        # Wait for the 'q' key to exit
        if cv2.waitKey(1) == ord('q'):
            break

    # Release the camera
    camera.release()

    # Close the window
    cv2.destroyAllWindows()

scan_qr_code()