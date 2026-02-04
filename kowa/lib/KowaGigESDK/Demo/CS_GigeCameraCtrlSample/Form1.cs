using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Runtime.InteropServices;
using System.Threading;
using System.Drawing.Imaging;

using OpenCvSharp;
using OpenCvSharp.Extensions;

namespace GigeCameraCtrlSample
{
    public partial class Form1 : Form
    {
        public static Form1 Instance { get; } = new Form1();

        KowaGigEVisionLib.DISCOVERY disccovery;
        KowaGigEVisionLib.CONNECTION connection;
        KowaGigEVisionLib.IMAGE_HEADER image_header;
        KowaGigEVisionLib.FEATURE_PARAMETER feature_param;

        KowaGigEVisionLib.CallbackDiscovery callback_discovery = new KowaGigEVisionLib.CallbackDiscovery(CallbackDisc);
        KowaGigEVisionLib.CallbackError callback_error = new KowaGigEVisionLib.CallbackError(CallbackErr);

        delegate void DisConnectDelegate(byte a);
        delegate void DelegateDraw();

        enum ACQUISITION_STATUS
        {
            DISCONNECT,
            CONNECT,
            ACQUISITION_START,
            ACQUISITION_STOP,
        };

        ACQUISITION_STATUS acquisitionStatus = ACQUISITION_STATUS.DISCONNECT;

        Int64 integer_value;
        double float_value;

        Bitmap grabBMP;

        string lStr, errorStr;
        ushort error;

        byte camera_device = 0;

        byte[] image_buffer = new byte[6144 * 6144];
        int image_width;
        int image_height;
        int image_size;

        const double target_frameRate = 15.0;

        public Form1()
        {
            InitializeComponent();
        }

        /*
          Callback Discovery Status
        */
        static void CallbackDisc(int s_cnt)
        {
            //Text output to console
            Console.WriteLine("Discovery in progress. Please wait. [{0:D} %]", s_cnt);
        }

        void update_log_text(string log)
        {
            try
            {
                if (InvokeRequired)
                {
                    Invoke((MethodInvoker)delegate () { textBoxInfo.AppendText(log); });
                }
                else
                {
                    textBoxInfo.AppendText(log);
                }
            }
            catch (Exception ee)
            {
                string msg = ee.Message;
            }
        }

        /*
          DisConnect Device
        */
        void disconnet(byte cam_nr)
        {
            if (acquisitionStatus != ACQUISITION_STATUS.DISCONNECT)
            {
                acquisitionStatus = ACQUISITION_STATUS.DISCONNECT;

                KowaGigEVisionLib.GEVAcquisitionStop(cam_nr);
                KowaGigEVisionLib.GEVCloseStreamChannel(cam_nr);
                KowaGigEVisionLib.GEVClose(cam_nr);

                buttonConnect.Enabled = true;
                buttonDisConnect.Enabled = false;

                btnSingleFrameStart.Enabled = true;
                btnContinuousStart.Enabled = true;
                btnContinuousStop.Enabled = false;

                groupBoxAcquisition.Enabled = false;
                groupBoxCameraParam.Enabled = false;
            }
        }

        void funcDisconnect(byte cam_nr)
        {
            if (InvokeRequired)
            {
                BeginInvoke(new DisConnectDelegate(disconnet), cam_nr);
            }
            else
            {
                disconnet(cam_nr);
            }
        }

        /*
          Error Callback Function
        */
        static void CallbackErr(byte cam_nr, IntPtr error_str)
        {
            string l_str = Marshal.PtrToStringAnsi(error_str);
            Console.WriteLine(l_str);

            Instance.update_log_text(l_str + "\r\n");

            byte status;
            byte eval;
            KowaGigEVisionLib.GEVGetConnectionStatus(cam_nr, out status, out eval);
            if (status == KowaGigEVisionLib.CONNECTION_STATUS_ACCESS_DENIED &&
                Instance.acquisitionStatus != ACQUISITION_STATUS.DISCONNECT)
            {
                Instance.funcDisconnect(cam_nr);
            }
        }

        /*
          Discovery Devices
        */
        private void buttonDetect_Click(object sender, EventArgs e)
        {
            // discovery devices on the ether-net.
            KowaGigEVisionLib.GEVDiscovery(out disccovery, callback_discovery, 400, false);

            comboBoxDetectList.Items.Clear();

            // if no device found, exit application
            if (disccovery.Count == 0)
            {
                textBoxInfo.AppendText("No GigE Device found\r\n");
            }
            else
            {
                for (int i = 0; i < disccovery.Count; i++)
                {
                    textBoxInfo.AppendText("GigE Device: " + (i + 1).ToString() + "\r\n");

                    System.Text.ASCIIEncoding enc = new System.Text.ASCIIEncoding();

                    textBoxInfo.AppendText(enc.GetString(disccovery.param[i].manuf) + "\r\n");
                    textBoxInfo.AppendText("\r\n");
                    textBoxInfo.AppendText(enc.GetString(disccovery.param[i].model) + "\r\n");
                    textBoxInfo.AppendText("\r\n");
                    textBoxInfo.AppendText(enc.GetString(disccovery.param[i].version) + "\r\n");
                    textBoxInfo.AppendText("\r\n");

                    //Providing It's IP address
                    lStr = (disccovery.param[i].IP & 0xFF) + "." +
                           ((disccovery.param[i].IP >> 8) & 0xFF) + "." +
                           ((disccovery.param[i].IP >> 16) & 0xFF) + "." +
                           ((disccovery.param[i].IP >> 24) & 0xFF);

                    string device_list_name = lStr + " / " + enc.GetString(disccovery.param[i].model);
                    comboBoxDetectList.Items.Add(device_list_name);

                    //Console.WriteLine(lStr);
                    textBoxInfo.AppendText("IP:" + lStr + "\r\n");

                    //Providing It's IP mask
                    lStr = "Adapter-Mask: " + (disccovery.param[i].AdapterMask & 0xFF) + "." +
                                              ((disccovery.param[i].AdapterMask >> 8) & 0xFF) + "." +
                                              ((disccovery.param[i].AdapterMask >> 16) & 0xFF) + "." +
                                               ((disccovery.param[i].AdapterMask >> 24) & 0xFF);

                    textBoxInfo.AppendText(lStr + "\r\n");

                    comboBoxDetectList.SelectedIndex = 0;

                    buttonConnect.Enabled = true;
                    buttonDisConnect.Enabled = false;
                }
            }
        }

        /*
          Device Parameter Set / Get
        */
        private bool init_device_param()
        {
            // Set stream channel packet delay to 500 (default 0)
            error = KowaGigEVisionLib.GEVSetFeatureInteger(camera_device, "GevSCPD", 500);
            if (error != KowaGigEVisionLib.GEV_STATUS_SUCCESS)
            {
                textBoxInfo.AppendText("[ERROR] - GEVSetFeatureInteger(GevSCPD): %s\r\n");
            }

            // Get packetsize parameters from xml node GevSCPSPacketSize
            error = KowaGigEVisionLib.GEVGetFeatureParameter(camera_device, "GevSCPSPacketSize", out feature_param);
            if (error != KowaGigEVisionLib.GEV_STATUS_SUCCESS)
            {
                KowaGigEVisionLib.GetErrorString(camera_device, error, out errorStr);
                textBoxInfo.AppendText("[ERROR] - GevSCPSPacketSize[" + errorStr + "]\r\n");
                return false;
            }
            else
            {
                // check parameters for correctness
                ushort ps_max, ps_min, ps_inc, packet_size;

                // calculate min, max and increment of packet size
                if (feature_param.Min == -1)
                    ps_min = 0;
                else
                    ps_min = (ushort)feature_param.Min;

                if (feature_param.Max == -1)
                    ps_max = 20000;
                else
                    ps_max = (ushort)feature_param.Max;

                ps_inc = (ushort)feature_param.Inc;
                if (ps_inc == 1)
                    ps_inc = 4;

                // test maximum achievable packet size
                error = KowaGigEVisionLib.GEVTestFindMaxPacketSize(camera_device, out packet_size, ps_min, ps_max, ps_inc);
                if (error != KowaGigEVisionLib.GEV_STATUS_SUCCESS)
                {
                    KowaGigEVisionLib.GetErrorString(camera_device, error, out errorStr);
                    textBoxInfo.AppendText("[ERROR] - GevSCPSPacketSize[" + errorStr + "]\r\n");
                    return false;
                }
                textBoxInfo.AppendText("[INFO] - Find maximal packet size: " + packet_size.ToString() + "\r\n");
                packet_size = (ushort)((ushort)packet_size / 2);
            }

            // Get current image width from the device
            error = KowaGigEVisionLib.GEVGetFeatureInteger(camera_device, "Width", out integer_value);
            if (error != KowaGigEVisionLib.GEV_STATUS_SUCCESS)
            {
                KowaGigEVisionLib.GetErrorString(camera_device, error, out errorStr);
                textBoxInfo.AppendText("[ERROR] - GEVGetFeatureInteger[" + errorStr + "]\r\n");
                return false;
            }
            image_width = (int)integer_value;

            // Get current image height from the device
            error = KowaGigEVisionLib.GEVGetFeatureInteger(camera_device, "Height", out integer_value);
            if (error != KowaGigEVisionLib.GEV_STATUS_SUCCESS)
            {
                KowaGigEVisionLib.GetErrorString(camera_device, error, out errorStr);
                textBoxInfo.AppendText("[ERROR] - GEVGetFeatureInteger[" + errorStr + "]\r\n");
                return false;
            }
            image_height = (int)integer_value;

            textBoxInfo.AppendText("[INFO] - Width: " + image_width.ToString() + "\r\n");
            textBoxInfo.AppendText("[INFO] - Height: " + image_height.ToString() + "\r\n");

            // Get current image size (payload size) from the device
            error = KowaGigEVisionLib.GEVGetFeatureInteger(camera_device, "PayloadSize", out integer_value);
            if (error != KowaGigEVisionLib.GEV_STATUS_SUCCESS)
            {
                KowaGigEVisionLib.GetErrorString(camera_device, error, out errorStr);
                textBoxInfo.AppendText("[ERROR] - GEVGetFeatureInteger[" + errorStr + "]\r\n");
                return false;
            }
            image_size = (int)integer_value;

            // Get current Gain (Float Node)
            KowaGigEVisionLib.GEVGetFeatureFloat(camera_device, "Gain", out float_value);
            textBoxGain.Text = float_value.ToString("F1");

            // Get current BinningType (Enumerate Node)
            StringBuilder str_binning_type = new StringBuilder();
            KowaGigEVisionLib.GEVGetFeatureEnumeration(camera_device, "BinningType", str_binning_type, 20);

            StringBuilder sb = new StringBuilder();
            bool loop = true;
            byte enum_index = 0;
            int item_index = 0;
            while (loop)
            {
                sb = new StringBuilder();
                error = KowaGigEVisionLib.GEVGetFeatureEnumerationName(camera_device, "BinningType", enum_index, sb, 20);
                if (sb.Length != 0)
                {
                    comboBoxBinningType.Items.Add(sb);
                    if (str_binning_type.Equals(sb))
                        item_index = enum_index;

                    enum_index++;
                }
                else
                {
                    loop = false;
                }
            }
            comboBoxBinningType.SelectedIndex = item_index;

            // Get current BinningDivider (Enumerate Node)
            StringBuilder str_binning_div = new StringBuilder();
            error = KowaGigEVisionLib.GEVGetFeatureEnumeration(camera_device, "BinningDivider", str_binning_div, 20);

            loop = true;
            enum_index = 0;
            item_index = 0;
            while (loop)
            {
                sb = new StringBuilder();
                error = KowaGigEVisionLib.GEVGetFeatureEnumerationName(camera_device, "BinningDivider", enum_index, sb, 20);
                if (sb.Length != 0)
                {
                    comboBoxBinningDivider.Items.Add(sb);
                    if (str_binning_div.Equals(sb))
                        item_index = enum_index;

                    enum_index++;
                }
                else
                {
                    loop = false;
                }
            }
            comboBoxBinningDivider.SelectedIndex = item_index;


            textBoxWidth.Text = image_width.ToString();
            textBoxHeight.Text = image_height.ToString();

            return true;
        }

        /*
          Connect Device (Connect Button Function)
        */
        private void buttonConnect_Click(object sender, EventArgs e)
        {
            if (acquisitionStatus != ACQUISITION_STATUS.DISCONNECT)
                return;

            if (comboBoxDetectList.Items.Count == 0)
                return;

            camera_device = (byte)(comboBoxDetectList.SelectedIndex + 1);

            // set disccovery parameter for GEVInit function
            connection.AdapterIP    = disccovery.param[camera_device - 1].AdapterIP;                 // network adapter ip address
            connection.AdapterMask  = disccovery.param[camera_device - 1].AdapterMask;             // network  adapter mask
            connection.IP_CANCam    = disccovery.param[camera_device - 1].IP;                        // device ip address
            connection.PortCtrl     = 49149;                                             // set 0 to port than automatic port is use
            connection.PortData     = 49150;                                             // set 0 to port than automatic port is use

            // name of network adapter
            connection.adapter_name = new char[disccovery.param[camera_device - 1].adapter_name.Length];
            Array.Copy(disccovery.param[camera_device - 1].adapter_name, connection.adapter_name, disccovery.param[camera_device - 1].adapter_name.Length);

            textBoxInfo.AppendText(connection.adapter_name + "\r\n");

            // init GigE device
            error = KowaGigEVisionLib.GEVInit(camera_device, ref connection, callback_error, 0, KowaGigEVisionLib.EXCLUSIVE_ACCESS);
            if (error != KowaGigEVisionLib.GEV_STATUS_SUCCESS)
            {
                KowaGigEVisionLib.GetErrorString(camera_device, error, out errorStr);
                textBoxInfo.AppendText("[ERROR] - GEVInit[" + errorStr + "]\r\n");
                return;
            }
            // init xml parser
            error = KowaGigEVisionLib.GEVInitXml(camera_device);
            if (error != KowaGigEVisionLib.GEV_STATUS_SUCCESS)
            {
                KowaGigEVisionLib.GetErrorString(camera_device, error, out errorStr);
                textBoxInfo.AppendText("[ERROR] - GEVInitXml[" + errorStr + "]\r\n");
                return;
            }

            //Enable Filter Driver
            KowaGigEVisionLib.GEVInitFilterDriver(camera_device);

            //Resend request mode
            KowaGigEVisionLib.GEVSetPacketResend(camera_device, 1);

            // open stream channel
            error = KowaGigEVisionLib.GEVOpenStreamChannel(camera_device, connection.AdapterIP, connection.PortData, 0);
            if (error != KowaGigEVisionLib.GEV_STATUS_SUCCESS)
            {
                KowaGigEVisionLib.GetErrorString(camera_device, error, out errorStr);
                textBoxInfo.AppendText("[ERROR] - GEVOpenStreamChannel[" + errorStr + "]\r\n");
                return;
            }

            if (init_device_param())
            {
                buttonConnect.Enabled = false;
                buttonDisConnect.Enabled = true;

                groupBoxAcquisition.Enabled = true;
                groupBoxCameraParam.Enabled = true;

                acquisitionStatus = ACQUISITION_STATUS.CONNECT;
            }
        }

        /*
          DisConnect Button Function
        */
        private void buttonDisConnect_Click(object sender, EventArgs e)
        {
            disconnet(camera_device);
        }

        /*
          SingleFrame Imaging and Draw
        */
        private void btnSingleFrameStart_Click(object sender, EventArgs e)
        {
            string acq_mode_value = "SingleFrame";
            StringBuilder acq_mode = new StringBuilder();
            acq_mode.Append(acq_mode_value);
            error = KowaGigEVisionLib.GEVSetFeatureEnumeration(camera_device, "AcquisitionMode", acq_mode, acq_mode_value.Length);

            // start acquisition of the picture data
            error = KowaGigEVisionLib.GEVAcquisitionStart(camera_device, 1);
            acquisitionStatus = ACQUISITION_STATUS.ACQUISITION_START;

            if (error != KowaGigEVisionLib.GEV_STATUS_SUCCESS)
            {
                KowaGigEVisionLib.GetErrorString(camera_device, error, out errorStr);
                textBoxInfo.AppendText("[ERROR] - GEVAcquisitionStart[" + errorStr + "]\r\n");
                return;
            }

            //initial settings
            image_header.FrameCounter = 0;
            image_header.TimeStamp = 0;
            image_header.PixelType = 0;
            image_header.SizeX = 0;
            image_header.SizeY = 0;
            image_header.OffsetX = 0;
            image_header.OffsetY = 0;

            try
            {
                // get image and header info  image_buffer is the data pointer
                error = KowaGigEVisionLib.GEVGetImageBuffer(camera_device, out image_header, image_buffer);
            }
            catch (Exception)
            {
                //continue;
            }

            if (error == KowaGigEVisionLib.GEV_STATUS_SUCCESS)
            {
                this.pictureBox1.Refresh();

                grabBMP = new Bitmap(image_width, image_height, PixelFormat.Format8bppIndexed);

                ColorPalette pal = grabBMP.Palette;

                for (int i = 0; i < pal.Entries.Length; i++)
                    pal.Entries[i] = Color.FromArgb(i, i, i);

                grabBMP.Palette = pal;

                BitmapData bmData = grabBMP.LockBits(new Rectangle(System.Drawing.Point.Empty, grabBMP.Size), ImageLockMode.WriteOnly, PixelFormat.Format8bppIndexed);

                IntPtr Iptr = IntPtr.Zero;
                Iptr = bmData.Scan0;
                Marshal.Copy(image_buffer, 0, Iptr, image_size);
                grabBMP.UnlockBits(bmData);

                Bitmap smallBMP = new Bitmap(grabBMP, image_width / 4, image_height / 4);
                this.pictureBox1.Image = smallBMP;
            }
            else
            {
                KowaGigEVisionLib.GetErrorString(camera_device, error, out errorStr);
                if (errorStr != null)
                {
                    textBoxInfo.AppendText("[ERROR] - GEVGetImageBuffer[" + errorStr + "]\r\n");
                }
            }

            KowaGigEVisionLib.GEVAcquisitionStop(camera_device);
            acquisitionStatus = ACQUISITION_STATUS.ACQUISITION_STOP;
        }

        private void DrawPicture()
        {
            Bitmap smallBMP = new Bitmap(grabBMP, image_width / 4, image_height / 4);//612, 512
            pictureBox1.Image = smallBMP;
        }

        /*
          Continuous Imaging Thread
        */
        private void ContinuousThreadProc()
        {
            DelegateDraw process = new DelegateDraw(DrawPicture);

            // start acquisition of the picture data
            error = KowaGigEVisionLib.GEVAcquisitionStart(camera_device, 0);
            acquisitionStatus = ACQUISITION_STATUS.ACQUISITION_START;

            //initial settings
            image_header.FrameCounter = 0;
            image_header.TimeStamp = 0;
            image_header.PixelType = 0;
            image_header.SizeX = 0;
            image_header.SizeY = 0;
            image_header.OffsetX = 0;
            image_header.OffsetY = 0;

            // Set Video Writer. In the below example, H264 is specified for VideoCodec. If you want to specify another Codec, specify it here.
            VideoWriter vw = new VideoWriter("output.mp4", FourCC.H264, (int)target_frameRate, new OpenCvSharp.Size(image_width, image_height));

            while (acquisitionStatus == ACQUISITION_STATUS.ACQUISITION_START)
            {
                // get images continiusly while not press stop button
                try
                {
                    // get image and header info  image_buffer is the data pointer
                    KowaGigEVisionLib.GEVGetImageBuffer(camera_device, out image_header, image_buffer);
                }
                catch (Exception)
                {
                    //continue;
                }

                grabBMP = new Bitmap(image_width, image_height, PixelFormat.Format8bppIndexed);

                ColorPalette pal = grabBMP.Palette;

                for (int i = 0; i < pal.Entries.Length; i++)
                    pal.Entries[i] = Color.FromArgb(i, i, i);

                grabBMP.Palette = pal;

                BitmapData bmData = grabBMP.LockBits(new Rectangle(System.Drawing.Point.Empty, grabBMP.Size), ImageLockMode.WriteOnly, PixelFormat.Format8bppIndexed);

                IntPtr Iptr = IntPtr.Zero;
                Iptr = bmData.Scan0;
                Marshal.Copy(image_buffer, 0, Iptr, image_size);
                grabBMP.UnlockBits(bmData);

                // Convert bitmap to mat to be handled by OpenCV
                Mat mat = OpenCvSharp.Extensions.BitmapConverter.ToMat(grabBMP);

                vw.Write(mat);

                this.Invoke(process);
            }

            // Dispose Video Writer
            vw.Dispose();
            KowaGigEVisionLib.GEVAcquisitionStop(camera_device);
            acquisitionStatus = ACQUISITION_STATUS.ACQUISITION_STOP;
        }

        /*
          Continuous  Start Function(Thread Start)
        */
        private void btnContinuousStart_Click(object sender, EventArgs e)
        {
            string acq_mode_value = "Continuous";
            StringBuilder acq_mode = new StringBuilder();
            acq_mode.Append(acq_mode_value);
            error = KowaGigEVisionLib.GEVSetFeatureEnumeration(camera_device, "AcquisitionMode", acq_mode, acq_mode_value.Length);

            // Set Frame Rate
            KowaGigEVisionLib.GEVSetFeatureFloat(camera_device, "AcquisitionFrameRate", target_frameRate);

            // Enable Frame Rate Control
            KowaGigEVisionLib.GEVSetFeatureBoolean(camera_device, "AcquisitionFrameRateEnable", 1); //1=True, 0= False

            Thread Continuous_thread = new Thread(new ThreadStart(ContinuousThreadProc));
            Continuous_thread.Start();

            groupBoxCameraParam.Enabled = false;

            btnSingleFrameStart.Enabled = false;
            btnContinuousStart.Enabled = false;
            btnContinuousStop.Enabled = true;
        }

        /*
          Continuous Stop Function(Thread Stop)
        */
        private void btnContinuousStop_Click(object sender, EventArgs e)
        {
            acquisitionStatus = ACQUISITION_STATUS.ACQUISITION_STOP;

            btnSingleFrameStart.Enabled = true;
            btnContinuousStart.Enabled = true;
            btnContinuousStop.Enabled = false;

            groupBoxCameraParam.Enabled = true;
        }

        /*
           Width & Height & Size Get Function
        */
        private void get_width_height_size()
        {
            error = KowaGigEVisionLib.GEVGetFeatureInteger(camera_device, "Width", out integer_value);
            if (error != KowaGigEVisionLib.GEV_STATUS_SUCCESS)
            {
                KowaGigEVisionLib.GetErrorString(camera_device, error, out errorStr);
                textBoxInfo.AppendText("[ERROR] - GEVGetFeatureInteger[" + errorStr + "]\r\n");
                return;
            }
            image_width = (int)integer_value;
            textBoxWidth.Text = image_width.ToString();

            error = KowaGigEVisionLib.GEVGetFeatureInteger(camera_device, "Height", out integer_value);
            if (error != KowaGigEVisionLib.GEV_STATUS_SUCCESS)
            {
                KowaGigEVisionLib.GetErrorString(camera_device, error, out errorStr);
                textBoxInfo.AppendText("[ERROR] - GEVGetFeatureInteger[" + errorStr + "]\r\n");
                return;
            }
            image_height = (int)integer_value;
            textBoxHeight.Text = image_height.ToString();

            error = KowaGigEVisionLib.GEVGetFeatureInteger(camera_device, "PayloadSize", out integer_value);
            if (error != KowaGigEVisionLib.GEV_STATUS_SUCCESS)
            {
                KowaGigEVisionLib.GetErrorString(camera_device, error, out errorStr);
                textBoxInfo.AppendText("[ERROR] - GEVGetFeatureInteger[" + errorStr + "]\r\n");
                return;
            }
            image_size = (int)integer_value;
        }

        /*
           Width Set Function (Integer Access Sample)
        */
        private void buttonSetWidth_Click(object sender, EventArgs e)
        {
            long width_val = Int32.Parse(textBoxWidth.Text);
            error = KowaGigEVisionLib.GEVSetFeatureInteger(camera_device, "Width", width_val);
            if (error != KowaGigEVisionLib.GEV_STATUS_SUCCESS)
            {
                KowaGigEVisionLib.GetErrorString(camera_device, error, out errorStr);
                textBoxInfo.AppendText("[ERROR] - GEVSetFeatureInteger[" + errorStr + "]\r\n");
                return;
            }

            get_width_height_size();
        }

        /*
           Width Get Function (Integer Access Sample)
        */
        private void buttonGetWidth_Click(object sender, EventArgs e)
        {
            get_width_height_size();
        }

        /*
           Height Set Function (Integer Access Sample)
        */
        private void buttonSetHeight_Click(object sender, EventArgs e)
        {
            long height_val = Int32.Parse(textBoxHeight.Text);
            error = KowaGigEVisionLib.GEVSetFeatureInteger(camera_device, "Height", height_val);
            if (error != KowaGigEVisionLib.GEV_STATUS_SUCCESS)
            {
                KowaGigEVisionLib.GetErrorString(camera_device, error, out errorStr);
                textBoxInfo.AppendText("[ERROR] - GEVSetFeatureInteger[" + errorStr + "]\r\n");
                return;
            }

            get_width_height_size();
        }

        /*
           Height Get Function (Integer Access Sample)
        */
        private void buttonGetHeight_Click(object sender, EventArgs e)
        {
            get_width_height_size();
        }

        /*
           Gain Set Function (Float Access Sample)
        */
        private void buttonSetGain_Click(object sender, EventArgs e)
        {
            float gain_val = float.Parse(textBoxGain.Text);
            error = KowaGigEVisionLib.GEVSetFeatureFloat(camera_device, "Gain", gain_val);
            if (error != KowaGigEVisionLib.GEV_STATUS_SUCCESS)
            {
                KowaGigEVisionLib.GetErrorString(camera_device, error, out errorStr);
                textBoxInfo.AppendText("[ERROR] - GEVSetFeatureInteger[" + errorStr + "]\r\n");
                return;
            }
        }

        /*
           Gain Get Function (Float Access Sample)
        */
        private void buttonGetGain_Click(object sender, EventArgs e)
        {
            error = KowaGigEVisionLib.GEVGetFeatureFloat(camera_device, "Gain", out float_value);
            if (error != KowaGigEVisionLib.GEV_STATUS_SUCCESS)
            {
                KowaGigEVisionLib.GetErrorString(camera_device, error, out errorStr);
                textBoxInfo.AppendText("[ERROR] - GEVGetFeatureInteger[" + errorStr + "]\r\n");
                return;
            }

            textBoxGain.Text = float_value.ToString("F1");
        }

        /*
           BinningType Set Function (enum Access Sample)
        */
        private void buttonSetBinningType_Click(object sender, EventArgs e)
        {
            StringBuilder sb = new StringBuilder();
            sb.Append(comboBoxBinningType.SelectedItem);
            error = KowaGigEVisionLib.GEVSetFeatureEnumeration(camera_device, "BinningType", sb, 20);
            if (error != KowaGigEVisionLib.GEV_STATUS_SUCCESS)
            {
                KowaGigEVisionLib.GetErrorString(camera_device, error, out errorStr);
                textBoxInfo.AppendText("[ERROR] - GEVSetFeatureEnumeration[" + errorStr + "]\r\n");
                return;
            }

            get_width_height_size();
            get_binning_divider();
        }

        /*
           BinningType Get Function (enum Access Sample)
        */
        private void buttonGetBinningType_Click(object sender, EventArgs e)
        {
            StringBuilder str_binning_type = new StringBuilder();
            error = KowaGigEVisionLib.GEVGetFeatureEnumeration(camera_device, "BinningType", str_binning_type, 20);
            if (error != KowaGigEVisionLib.GEV_STATUS_SUCCESS)
            {
                KowaGigEVisionLib.GetErrorString(camera_device, error, out errorStr);
                textBoxInfo.AppendText("[ERROR] - GEVGetFeatureInteger[" + errorStr + "]\r\n");
                return;
            }

            for (int i = 0; i < comboBoxBinningType.Items.Count; ++i)
            {
                StringBuilder temp = new StringBuilder();
                temp.Append(comboBoxBinningType.Items[i].ToString());
                if (temp.Equals(str_binning_type))
                {
                    comboBoxBinningType.SelectedIndex = i;
                    break;
                }
            }
        }

        /*
           BinningDivider Set Function (enum Access Sample)
        */
        private void buttonSetBinningDivider_Click(object sender, EventArgs e)
        {
            StringBuilder sb = new StringBuilder();
            sb.Append(comboBoxBinningDivider.SelectedItem);
            error = KowaGigEVisionLib.GEVSetFeatureEnumeration(camera_device, "BinningDivider", sb, 20);
            if (error != KowaGigEVisionLib.GEV_STATUS_SUCCESS)
            {
                KowaGigEVisionLib.GetErrorString(camera_device, error, out errorStr);
                textBoxInfo.AppendText("[ERROR] - GEVSetFeatureEnumeration[" + errorStr + "]\r\n");
                return;
            }
        }

        /*
           BinningDivider Get Function (enum Access Sample)
        */
        private void get_binning_divider()
        {
            StringBuilder str_binning_div = new StringBuilder();
            error = KowaGigEVisionLib.GEVGetFeatureEnumeration(camera_device, "BinningDivider", str_binning_div, 20);
            if (error != KowaGigEVisionLib.GEV_STATUS_SUCCESS)
            {
                KowaGigEVisionLib.GetErrorString(camera_device, error, out errorStr);
                textBoxInfo.AppendText("[ERROR] - GEVGetFeatureInteger[" + errorStr + "]\r\n");
                return;
            }

            for (int i = 0; i < comboBoxBinningDivider.Items.Count; ++i)
            {
                StringBuilder temp = new StringBuilder();
                temp.Append(comboBoxBinningDivider.Items[i].ToString());
                if (temp.Equals(str_binning_div))
                {
                    comboBoxBinningDivider.SelectedIndex = i;
                    break;
                }
            }
        }

        private void buttonGetBinningDivider_Click(object sender, EventArgs e)
        {
            get_binning_divider();
        }

        private void button_clear_Click(object sender, EventArgs e)
        {
            textBoxInfo.Clear();
        }

        private void Form1_FormClosing(object sender, FormClosingEventArgs e)
        {
            disconnet(camera_device);
        }
    }
}
