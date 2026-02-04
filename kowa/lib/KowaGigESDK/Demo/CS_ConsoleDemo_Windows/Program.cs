/*****************************************************************************/
/*
 *  Program.cs      -- sample application to use discover, open, configure
 *                     and stream from a GigE Vision device
 *
 *****************************************************************************
 * This sample demonstrates how to use the GigE Vision library to
 * discover and open a GigE Vision device. Reading and writing devices registers
 * and stream images is also demonstrated.
 * For reference of the uses KowaGigEVisionLib library function, refer to its documentation.
 * The code is delivered "as is" without any warranty and can be freely used
 * for own applications.
 */
/*****************************************************************************/
using System;
using Kowa.GigEVision;

namespace ConsoleDemo
{
    class Program
    {
        static void Main(string[] args)
        {
            KowaGigEVisionLib.Discovery(out Discovery d, CallbackDiscovery, 1000, false);
            Console.WriteLine($"Discovered camera count: {d.Count}");

            if (d.Count == 0) throw new Exception("No GigE Device found.");
            DeviceParameter target = d[0];

            //KowaGigEVisionLib.ForceIp(target, "192.168.1.8");
            //KowaGigEVisionLib.Discovery(out d, CallbackDiscovery, 1000, false);
            //target = d[0];

            using (Camera camera = KowaGigEVisionLib.Init(target, null, false, OpenMode.Exclusive))
            {
                camera.InitXml();
                camera.InitFilterDriver();
                camera.OpenStreamChannel();
                //camera.OpenStreamChannel("239.1.16.1");
                camera.SetPacketResend(true);
                camera.SetValue("GevSCPD", 500);
                camera.SetValue("ExposureTime", 15000);

                camera.GetValue("Height", out int height);
                camera.GetValue("Width", out int width);
                camera.GetValue("PayloadSize", out int payload_size);
                camera.GetValue("PixelFormat", out Kowa.GigEVision.PfncFormat pixformat);

                Console.WriteLine($"Height: {height}");
                Console.WriteLine($"Width: {width}");
                Console.WriteLine($"PayloadSize: {payload_size}");
                Console.WriteLine($"PixelFormat: {pixformat}");

                byte[] image_buffer = new byte[payload_size];
                camera.AcquisitionStart(0);
                for (int i = 0; i < 16; ++i)
                {
                    try
                    {
                        var header = camera.GetImageBuffer(image_buffer);
                        WriteGrayscaleBitmapFile($"{i}.bmp", image_buffer, width, height);
                    }
                    catch (Kowa.GigEVision.GrabException ex)
                    {
                        Console.WriteLine(ex);
                        Console.WriteLine($"frame: {ex.ImageHeader.FrameCounter}, missing packet: {ex.ImageHeader.MissingPacket}");
                    }
                }

                camera.AcquisitionStop();
                camera.CloseStreamChannel();
                camera.Close();
            }
        }

        // discovery callback funtion
        static void CallbackDiscovery(int s_cnt, DeviceParameter? dev)
        {
            Console.WriteLine("Discovery in progress. Please wait. [{0:D} %]", s_cnt);
        }

        static void WriteGrayscaleBitmapFile(string filepath, byte[] buffer, int width, int height)
        {
            using (var sw = System.IO.File.OpenWrite(filepath))
            using (var writer = new System.IO.BinaryWriter(sw))
            {
                // BITMAPFILEHEADER
                writer.Write((byte)'B');
                writer.Write((byte)'M');
                writer.Write((uint)(14 + 40 + 1024 + buffer.Length));
                writer.Write((ushort)0);
                writer.Write((ushort)0);
                writer.Write((uint)(14 + 40 + 1024));

                // BITMAPINFOHEADER
                writer.Write((uint)40);
                writer.Write((int)width);
                writer.Write((int)height);
                writer.Write((ushort)1);
                writer.Write((ushort)8);
                writer.Write((uint)0);
                writer.Write((uint)buffer.Length);
                writer.Write((int)0);
                writer.Write((int)0);
                writer.Write((uint)256);
                writer.Write((uint)0);

                // pallet
                foreach (var j in System.Linq.Enumerable.Range(0, 256))
                {
                    writer.Write((byte)j);
                    writer.Write((byte)j);
                    writer.Write((byte)j);
                    writer.Write((byte)0);
                }

                for (int y = 0; y < height; y++)
                {
                    writer.Write(buffer, (height - y - 1) * width, width);
                }
            }
            string full_filepath = System.IO.Path.Combine(System.IO.Directory.GetCurrentDirectory(), filepath);
            Console.WriteLine($"wrote captured image: {full_filepath}");
        }
    }
}
